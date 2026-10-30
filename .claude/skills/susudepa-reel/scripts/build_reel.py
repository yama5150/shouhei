#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
縦型リールのビルダー。JSON の構成ファイルを読んで mp4 とサムネを書き出す。

    python3 build_reel.py config.json
    python3 build_reel.py config.json --audio-only   # 映像を作り直さない
    python3 build_reel.py config.json --cover-only   # サムネだけ

映像は 1 回だけエンコードして、音声違いを差し替えで mux する。構成を
変えていないときに音量だけ直したい場合は --audio-only が速い。

構成ファイルの書き方は references/config.md を参照。
"""

import json
import subprocess
import sys
from pathlib import Path

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/motoya-l-maruberi/MTLmr3m.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]

DEFAULTS = {
    "size": [1080, 1920],
    "fps": 30,
    "crf": 20,
    # 書き出しの音量。SNS 向け
    "target_lufs": -16.0,
    "peak_ceiling": 0.84,          # -1.5dBFS。リミッターの頭打ち
    # テロップ
    "caption_bottom": 1410,        # Instagram の UI に被らない高さ
    "line_step": 118,
    "card_line_step": 146,
    "text_in": 0.15,
    "chip": "0x101010@0.60",
    # 下地を敷かずに縁取りで読ませたいとき用。0 なら縁取り無し（既定）
    "caption_border": 0,
    "caption_border_color": "black@0.85",
    "ink": "white",
    "accent": "0xF0C071",
    # 前後
    "fade_in": 0.0,                # 1 フレーム目を黒くしないため既定は 0
    "fade_out": 0.20,
    "audio_tail": 3.5,
    "audio_curve": "tri",
    # 色
    "grade": "eq=contrast=1.05:saturation=1.16:gamma=1.06",
    "sharpen": "unsharp=5:5:0.45:5:5:0.0",
}


def die(msg):
    sys.exit(f"エラー: {msg}")


def run(cmd, what):
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        die(f"ffmpeg が失敗しました ({what})")


def loudnorm_json(cmd, what):
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        die(f"音量測定に失敗しました ({what})")
    s = proc.stderr
    return json.loads(s[s.rfind("{"):s.rfind("}") + 1])


class Reel:
    def __init__(self, cfg_path):
        self.cfg_path = Path(cfg_path).resolve()
        cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.c = {**DEFAULTS, **cfg}
        self.name = self.c.get("name") or self.cfg_path.stem
        self.W, self.H = self.c["size"]
        self.fps = self.c["fps"]

        base = self.cfg_path.parent
        self.src = (base / self.c.get("src", ".")).resolve()
        self.out = (base / self.c.get("out", "out")).resolve()
        self.tmp = self.out / f"_{self.name}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)

        self.sources = {k: self.src / v for k, v in self.c.get("sources", {}).items()}
        self.segments = self.c["segments"]
        self.total = round(sum(s["dur"] for s in self.segments), 3)

        self.font = next((f for f in FONT_CANDIDATES if Path(f).exists()), None)
        if not self.font:
            die("日本語フォントが見つかりません (fonts-noto-cjk を入れてください)")

    # ---------------------------------------------------------- 部品

    def path_of(self, seg):
        key = seg.get("src")
        if not key:
            return None
        if key not in self.sources:
            die(f"sources に '{key}' がありません")
        p = self.sources[key]
        if not p.exists():
            die(f"素材が見つかりません: {p}")
        return p

    def grade(self, lift=1.0):
        """色調整。lift は暗いカットを持ち上げるガンマ。

        ガンマだけ上げると平坦になるので、少しコントラストを足し戻す。
        """
        extra = f",eq=gamma={lift:.2f}:contrast=1.03" if lift > 1.0 else ""
        return f"{self.c['grade']}{extra},{self.c['sharpen']}"

    def kenburns(self, zoom, dur, focus):
        """静止画のゆっくりズーム。

        2 倍解像度の台紙に載せてから zoompan で寄る。等倍のまま寄ると座標の
        丸めでカクつく。ffmpeg 6.x の crop には eval=frame が無いので、
        時間で変わる切り出しは zoompan でやるしかない。
        """
        z0, z1 = zoom if isinstance(zoom, (list, tuple)) else (zoom, zoom)
        fx, fy = focus
        bw, bh = self.W * 2, self.H * 2
        n = max(int(round(dur * self.fps)) - 1, 1)
        return (
            f"scale={bw}:{bh}:force_original_aspect_ratio=increase,"
            f"crop={bw}:{bh}:(iw-ow)*{fx:.3f}:(ih-oh)*{fy:.3f},"
            f"zoompan=z='{z0}+({z1}-{z0})*on/{n}':"
            f"x='(iw-iw/zoom)*{fx:.3f}':y='(ih-ih/zoom)*{fy:.3f}':"
            f"d=1:s={self.W}x{self.H}:fps={self.fps}"
        )

    def blur_fit(self, tag):
        """素材を切らずに全部見せる。余白は同じ絵をぼかして埋める。

        9:16 でない素材（4:3 の写真、小さい生成動画など）を切ると大事なものが
        落ちるうえ、拡大率も上がる。幅だけ合わせれば拡大は最小で済む。
        """
        return (
            f"split=2[bg{tag}][fg{tag}];"
            f"[bg{tag}]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
            f"crop={self.W}:{self.H},gblur=sigma=44,"
            f"eq=brightness=-0.10:saturation=0.60,fps={self.fps}[bgo{tag}];"
            f"[fg{tag}]scale={self.W}:-2:flags=lanczos,fps={self.fps}[fgo{tag}];"
            f"[bgo{tag}][fgo{tag}]overlay=x=(main_w-overlay_w)/2:"
            f"y=(main_h-overlay_h)/2:shortest=1"
        )

    def punch_in(self, zoom, focus):
        """動画を固定倍率で寄せる。構図の整理用。"""
        if not zoom or zoom <= 1.0:
            return ""
        fx, fy = focus
        cw = f"floor({self.W}/{zoom}/2)*2"
        ch = f"floor({self.H}/{zoom}/2)*2"
        return (
            f",crop=w={cw}:h={ch}:x='(in_w-out_w)*{fx:.3f}':"
            f"y='(in_h-out_h)*{fy:.3f}',scale={self.W}:{self.H}"
        )

    def captions(self, seg, idx, step=None):
        lines = [l for l in seg.get("lines", []) if l and l[0]]
        if not lines:
            return ""
        step = step or self.c["line_step"]
        first_y = self.c["caption_bottom"] - step * len(lines)
        # 下地を薄くする／外すときは、縁取りが無いと明るい絵の上で消える
        bw = self.c["caption_border"]
        border = (f"borderw={bw}:bordercolor={self.c['caption_border_color']}:"
                  if bw else "")
        parts = []
        for i, line in enumerate(lines):
            text = line[0]
            size = line[1] if len(line) > 1 else 64
            color = line[2] if len(line) > 2 else self.c["ink"]
            color = {"ink": self.c["ink"], "accent": self.c["accent"]}.get(color, color)
            tf = self.tmp / f"text{idx:02d}_{i}.txt"
            tf.write_text(text, encoding="utf-8")
            parts.append(
                f"drawtext=fontfile='{self.font}':textfile='{tf}':"
                f"fontsize={size}:fontcolor={color}:"
                f"box=1:boxcolor={self.c['chip']}:boxborderw=24:"
                f"{border}"
                f"shadowcolor=black@0.5:shadowx=0:shadowy=3:"
                f"x='(w-text_w)/2':y={first_y + step * i}:"
                f"enable='gte(t,{self.c['text_in']})'"
            )
        return "," + ",".join(parts)

    # ---------------------------------------------------------- 映像

    def render_video(self):
        inputs, chains, labels = [], [], []
        for i, seg in enumerate(self.segments):
            dur = seg["dur"]
            kind = seg.get("kind", "photo")
            lift = seg.get("lift", 1.0)
            focus = seg.get("focus", [0.5, 0.5])
            path = self.path_of(seg)

            if kind == "black":
                inputs += ["-f", "lavfi", "-t", f"{dur}",
                           "-i", f"color=c=black:s={self.W}x{self.H}:r={self.fps}"]
                chains.append(
                    f"[{i}:v]trim=duration={dur},setpts=PTS-STARTPTS,"
                    f"setsar=1,format=yuv420p[v{i}]")
            elif kind == "card":
                # 写真を大きくぼかして暗く落とし、文字だけ載せる。ロゴが黒地なら
                # カードも暗くしておくとつながりがいい
                inputs += ["-loop", "1", "-framerate", str(self.fps),
                           "-t", f"{dur}", "-i", str(path)]
                chains.append(
                    f"[{i}:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
                    f"crop={self.W}:{self.H},gblur=sigma=56,"
                    f"eq=brightness=-0.26:saturation=0.40:gamma={lift:.2f},"
                    f"fps={self.fps},setsar=1,format=yuv420p"
                    f"{self.captions(seg, i, self.c['card_line_step'])}[v{i}]")
            elif kind == "photo":
                # iPhone の JPEG は EXIF の回転を ffmpeg が自動で当てる。
                # ここで transpose を足すと二重回転になる
                inputs += ["-loop", "1", "-framerate", str(self.fps),
                           "-t", f"{dur}", "-i", str(path)]
                if seg.get("fit") == "blur":
                    shaper = self.blur_fit(f"p{i}")
                else:
                    shaper = self.kenburns(seg.get("zoom", [1.0, 1.08]), dur, focus)
                chains.append(
                    f"[{i}:v]{shaper},{self.grade(lift)},fps={self.fps},"
                    f"setsar=1,format=yuv420p{self.captions(seg, i)}[v{i}]")
            else:  # video
                inputs += ["-ss", f"{seg.get('start', 0)}", "-t", f"{dur}", "-i", str(path)]
                if seg.get("plain"):
                    # ロゴなど完成済みの素材。色もテロップも足さない
                    look = f"scale={self.W}:{self.H}:flags=lanczos,setsar=1,format=yuv420p"
                    cap = ""
                elif seg.get("fit") == "blur":
                    look = f"{self.blur_fit(f'v{i}')},{self.grade(lift)},setsar=1,format=yuv420p"
                    cap = self.captions(seg, i)
                else:
                    look = (
                        f"scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
                        f"crop={self.W}:{self.H}{self.punch_in(seg.get('zoom', 1.0), focus)},"
                        f"{self.grade(lift)},setsar=1,format=yuv420p")
                    cap = self.captions(seg, i)
                chains.append(
                    f"[{i}:v]fps={self.fps},{look},"
                    f"trim=duration={dur},setpts=PTS-STARTPTS{cap}[v{i}]")
            labels.append(f"[v{i}]")

        chains.append("".join(labels) + f"concat=n={len(self.segments)}:v=1:a=0[vcat]")
        fi = f"fade=t=in:st=0:d={self.c['fade_in']}," if self.c["fade_in"] > 0 else ""
        chains.append(
            f"[vcat]{fi}fade=t=out:"
            f"st={self.total - self.c['fade_out']:.3f}:d={self.c['fade_out']}[vout]")

        script = self.tmp / "fg_video.txt"
        script.write_text(";\n".join(chains), encoding="utf-8")
        dest = self.tmp / "video.mp4"
        print(f"→ 映像 ({self.total:.1f}秒) をエンコード中…")
        run(["ffmpeg", "-hide_banner", "-y"] + inputs +
            ["-filter_complex_script", str(script), "-map", "[vout]", "-an",
             "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
             "-preset", "slow", "-crf", str(self.c["crf"]), "-pix_fmt", "yuv420p",
             "-r", str(self.fps), "-g", str(self.fps * 2), "-movflags", "+faststart",
             "-t", f"{self.total:.3f}", str(dest)], "映像")
        return dest

    # ---------------------------------------------------------- 音声

    def has_audio(self, path):
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True)
        return "audio" in r.stdout

    def measure(self, inputs, chains, label, what):
        """グラフ途中のラベルの統合ラウドネスを測るだけ。

        loudnorm は測定にだけ使う。書き出しに通すと動的モードで音が暴れるし、
        先読み 3 秒ぶん末尾が落ちることがある（references/gotchas.md）。
        """
        graph = ";\n".join(chains + [f"[{label}]loudnorm=print_format=json[probe]"])
        script = self.tmp / f"fg_measure_{what}.txt"
        script.write_text(graph, encoding="utf-8")
        d = loudnorm_json(
            ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs +
            ["-filter_complex_script", str(script), "-map", "[probe]", "-vn",
             "-t", f"{self.total:.3f}", "-f", "null", "-"], what)
        return float(d["input_i"])

    def measure_file(self, path, start):
        d = loudnorm_json(
            ["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{start}",
             "-t", f"{self.total:.3f}", "-i", str(path),
             "-af", "loudnorm=print_format=json", "-f", "null", "-"], "music")
        return float(d["input_i"])

    def render_audio(self, with_music):
        kind = "music" if with_music else "ambient"
        print(f"→ 音声 ({kind}) を書き出し中…")
        music = self.c.get("music") or {}
        use_clip = music.get("use_clip_audio", True)

        inputs, chains, labels = [], [], []
        for i, seg in enumerate(self.segments):
            dur = seg["dur"]
            path = self.path_of(seg)
            if (use_clip and seg.get("kind") == "video"
                    and path is not None and self.has_audio(path)):
                inputs += ["-ss", f"{seg.get('start', 0)}", "-t", f"{dur}", "-i", str(path)]
                chains.append(
                    f"[{i}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:"
                    f"channel_layouts=stereo,atrim=duration={dur},asetpts=PTS-STARTPTS,"
                    f"afade=t=in:st=0:d=0.08,"
                    f"afade=t=out:st={dur - 0.08:.3f}:d=0.08[a{i}]")
            else:
                inputs += ["-f", "lavfi", "-t", f"{dur}",
                           "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
                chains.append(f"[{i}:a]atrim=duration={dur},asetpts=PTS-STARTPTS[a{i}]")
            labels.append(f"[a{i}]")

        n = len(self.segments)
        chains.append("".join(labels) + f"concat=n={n}:v=0:a=1[acat]")

        if with_music:
            mpath = (self.src / music["file"]) if not Path(music["file"]).is_absolute() \
                else Path(music["file"])
            if not mpath.exists():
                die(f"音源が見つかりません: {mpath}")
            start = music.get("start", 0)
            mlufs = music.get("lufs", -18.0)
            mi = self.measure_file(mpath, start)
            inputs += ["-ss", f"{start}", "-t", f"{self.total}", "-i", str(mpath)]
            chains.append(
                f"[{n}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:"
                f"channel_layouts=stereo,atrim=duration={self.total},"
                f"asetpts=PTS-STARTPTS,volume={mlufs - mi:+.2f}dB[musicout]")
            if use_clip:
                clufs = music.get("clip_lufs", -22.0)
                ci = self.measure(inputs[:-6], chains[:-1], "acat", f"{kind}_clips")
                print(f"   クリップ {ci:.1f} → {clufs} / 音楽 {mi:.1f} → {mlufs} LUFS")
                chains.append(f"[acat]volume={clufs - ci:+.2f}dB[clips]")
                chains.append(
                    "[clips][musicout]amix=inputs=2:duration=first:normalize=0[mix]")
            else:
                print(f"   音楽 {mi:.1f} → {mlufs} LUFS（曲のみ）")
                chains.append("[acat]anullsink")
                chains.append("[musicout]anull[mix]")
        else:
            chains.append("[acat]anull[mix]")

        mix_i = self.measure(inputs, chains, "mix", kind)
        gain = self.c["target_lufs"] - mix_i
        print(f"   全体 {mix_i:.1f} LUFS → {gain:+.1f}dB")
        tail = self.c["audio_tail"]
        chains.append(
            f"[mix]volume={gain:+.2f}dB,"
            f"alimiter=limit={self.c['peak_ceiling']:.3f}:level=disabled:"
            f"attack=5:release=60,"
            f"afade=t=in:st=0:d=0.20,"
            f"afade=t=out:st={self.total - tail:.3f}:d={tail}:"
            f"curve={self.c['audio_curve']}[aout]")

        script = self.tmp / f"fg_audio_{kind}.txt"
        script.write_text(";\n".join(chains), encoding="utf-8")
        dest = self.tmp / f"audio_{kind}.m4a"
        run(["ffmpeg", "-hide_banner", "-y"] + inputs +
            ["-filter_complex_script", str(script), "-map", "[aout]", "-vn",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-t", f"{self.total:.3f}", str(dest)], f"音声 {kind}")
        return dest

    # ---------------------------------------------------------- 仕上げ

    def mux(self, video, audio, outfile):
        dest = self.out / outfile
        args = ["ffmpeg", "-hide_banner", "-y", "-i", str(video)]
        if audio:
            args += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy"]
        else:
            args += ["-map", "0:v:0", "-an", "-c", "copy"]
        run(args + ["-movflags", "+faststart", str(dest)], outfile)
        print(f"   完成: {dest}  {dest.stat().st_size / 1e6:.1f}MB")
        return dest

    def build_cover(self):
        """サムネ。タイトルは make_title.py が描いた PNG を重ねるだけ。

        ffmpeg の drawtext はカラー絵文字を描けないので、文字と絵文字は
        Pillow 側で作る（references/gotchas.md）。
        """
        cv = self.c.get("cover")
        if not cv:
            return None
        base = self.sources.get(cv["base"])
        if not base or not base.exists():
            die(f"サムネの素材が見つかりません: {cv.get('base')}")
        title = self.out / cv.get("title", "title.png")
        lift = cv.get("lift", 1.0)

        if title.exists():
            graph = (
                f"[0:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
                f"crop={self.W}:{self.H},{self.grade(lift)},eq=brightness=-0.04[bg];"
                f"[bg][1:v]overlay=x=(W-w)/2:y={cv.get('title_y', 470)}[out]")
            ins = ["-i", str(base), "-i", str(title)]
        else:
            print("   （title.png が無いので、地の写真だけでサムネを作る）")
            graph = (
                f"[0:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
                f"crop={self.W}:{self.H},{self.grade(lift)}[out]")
            ins = ["-i", str(base)]

        script = self.tmp / "fg_cover.txt"
        script.write_text(graph, encoding="utf-8")
        dest = self.out / cv.get("file", f"{self.name}_cover.jpg")
        print("→ サムネを書き出し中…")
        run(["ffmpeg", "-hide_banner", "-y"] + ins +
            ["-filter_complex_script", str(script), "-map", "[out]",
             "-frames:v", "1", "-q:v", "2", str(dest)], "サムネ")
        print(f"   完成: {dest}")
        return dest

    def build(self, audio_only=False, cover_only=False):
        if cover_only:
            return self.build_cover()
        cached = self.tmp / "video.mp4"
        video = cached if (audio_only and cached.exists()) else self.render_video()
        if video == cached and audio_only:
            print(f"→ 映像は既存のものを使う: {cached}")

        stem = self.c.get("basename", self.name)
        music = self.c.get("music") or {}
        has_music = bool(music.get("file"))
        self.mux(video, None, f"{stem}_muted.mp4")
        if has_music:
            self.mux(video, self.render_audio(True), f"{stem}.mp4")
        elif (self.c.get("music") or {}).get("ambient", True) and self.any_clip_audio():
            self.mux(video, self.render_audio(False), f"{stem}.mp4")
        else:
            self.mux(video, None, f"{stem}.mp4")
        self.build_cover()

    def any_clip_audio(self):
        for seg in self.segments:
            p = self.path_of(seg)
            if seg.get("kind") == "video" and p and self.has_audio(p):
                return True
        return False


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    Reel(args[0]).build(
        audio_only="--audio-only" in sys.argv,
        cover_only="--cover-only" in sys.argv,
    )
