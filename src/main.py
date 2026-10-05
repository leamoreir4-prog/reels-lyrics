import datetime as dt, json, os, random, tempfile
from . import config as C, drive, lyrics, render

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "used.json")
UTC = dt.timezone.utc


def load_state():
    try:
        d = json.load(open(STATE))
    except Exception:
        d = {}
    return d.get("used", []), d.get("slots", [])


def save_state(used, slots):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"used": used, "slots": slots[-20:]}, open(STATE, "w"), indent=1)


def make_reel(files, audios, used, work):
    """Elige canción, arma letra y fondo y renderiza. Devuelve (ruta_mp4, canción)."""
    pool = [a for a in audios if a["id"] not in used]
    if not pool:                                # ya sonaron todos: reinicia la rotación
        used.clear()
        pool = audios
    song = random.choice(pool)
    print("Canción elegida:", song["name"])

    audio = drive.download(song, os.path.join(work, "audio" + os.path.splitext(song["name"])[1]))
    start = drive.start_offset(song["name"])
    dur = min(C.MAX_SECONDS, render.audio_duration(audio) - start)
    if dur < 3:
        raise SystemExit("El audio (o el tramo elegido) dura menos de 3 s")

    srt = drive.find_srt(song["name"], files)
    if srt:
        print("Usando letra manual (.srt)")
        lines = lyrics.parse_srt(drive.download(srt, os.path.join(work, "l.srt")), 0, dur)
    else:
        clip = os.path.join(work, "clip.wav")
        os.system(f'ffmpeg -y -v error -ss {start} -t {dur} -i "{audio}" -ac 1 -ar 16000 "{clip}"')
        lines = lyrics.transcribe(clip, dur)
    print("Líneas de letra:", len(lines))

    photo_folder = os.getenv("DRIVE_PHOTOS_FOLDER_ID", "").strip()
    pfiles = drive.list_files(photo_folder) if photo_folder else files
    imgs = [f for f in pfiles if drive.is_image(f)]
    print(f"Archivos en la carpeta de fotos: {len(pfiles)} | fotos válidas (jpg/png/webp): {len(imgs)}")
    if photo_folder and not imgs:
        raise SystemExit("No encontré fotos en la carpeta de fotos de Drive. Revisá que esté compartida "
                         "con el email de la cuenta de servicio y que las fotos sean jpg, png o webp (no HEIC).")
    if len(imgs) > 4:
        imgs = random.sample(imgs, 4)           # cada reel usa 4 fotos distintas
    photos = [drive.download(im, os.path.join(work, f"foto{i}{os.path.splitext(im['name'])[1] or '.jpg'}"))
              for i, im in enumerate(imgs)]

    out = os.path.join(work, f"reel_{random.randint(1000, 9999)}.mp4")
    render.render(audio, start, dur, lines, work, out, photos)
    return out, song


def main():
    now = dt.datetime.now(UTC)
    dry = os.getenv("DRY_RUN") == "1"
    now_mode = os.getenv("PUBLISH_NOW") == "true"
    test_sched = os.getenv("TEST_SCHEDULE") == "true"
    work = tempfile.mkdtemp()
    used, done_slots = load_state()

    files = drive.list_files()
    audios = [f for f in files if drive.is_audio(f)]
    if not audios:
        raise SystemExit("No hay audios en la carpeta de Drive")
    from . import facebook

    if dry:
        out, _ = make_reel(files, audios, used, work)
        os.replace(out, "reel_preview.mp4")
        print("DRY_RUN: guardado reel_preview.mp4")
        return

    if test_sched:                               # prueba: programar un reel para dentro de 30 min
        out, song = make_reel(files, audios, used, work)
        when = now + dt.timedelta(minutes=30)
        vid = facebook.publish_reel(out, "", scheduled_ts=when.timestamp())
        print(f"PRUEBA: reel {vid} programado para {when.isoformat()} (UTC). "
              "Revisá en Meta Business Suite > Planificador que figure como programado.")
        return

    if now_mode:                                 # publicar ya (prueba manual)
        out, song = make_reel(files, audios, used, work)
        print("Publicado, video id:", facebook.publish_reel(out, ""))
        used.append(song["id"]); save_state(used, done_slots)
        return

    # --- ejecución diaria: deja programados los reels de hoy (14:00 y 18:00 de Uruguay) ---
    pending = []
    for h, m in C.SLOTS_UTC:
        slot = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if slot.isoformat() not in done_slots:
            pending.append(slot)
    if not pending:
        print("Los reels de hoy ya están programados. Nada que hacer.")
        return

    for slot in pending:
        target = slot + dt.timedelta(seconds=random.randint(0, C.JITTER_MIN * 60))
        ahead = (target - dt.datetime.now(UTC)).total_seconds() / 60
        if ahead < C.MIN_AHEAD_MIN and (dt.datetime.now(UTC) - slot).total_seconds() / 60 > C.LATE_LIMIT_MIN:
            print(f"Horario {slot.isoformat()} ya pasó hace demasiado; se omite.")
            done_slots.append(slot.isoformat())
            continue
        out, song = make_reel(files, audios, used, work)
        ahead = (target - dt.datetime.now(UTC)).total_seconds() / 60
        if ahead >= C.MIN_AHEAD_MIN:
            vid = facebook.publish_reel(out, "", scheduled_ts=target.timestamp())
            print(f"Reel {vid} programado en Facebook para {target.isoformat()} (UTC)")
        else:
            vid = facebook.publish_reel(out, "")
            print(f"Reel {vid} publicado de inmediato (el horario ya estaba encima)")
        used.append(song["id"])
        done_slots.append(slot.isoformat())
        save_state(used, done_slots)             # se guarda tras cada reel (los commits los hace el workflow)


if __name__ == "__main__":
    main()
