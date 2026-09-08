"""Fixed local CPU STT worker. No URLs, shells, configurable model or downloads."""
import json
import sys
import os
import resource

def decode_bounded(path):
    import av
    import numpy as np
    frames = []
    count = 0
    with av.open(path, options={'protocol_whitelist': 'file,pipe'}) as container:
        if not container.streams.audio:
            raise ValueError('audio')
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        stream = container.streams.audio[0]
        stream.thread_type = 'NONE'
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                count += out.samples
                if count > 320000:
                    raise ValueError('duration')
                frames.append(out.to_ndarray().flatten())
        for out in resampler.resample(None):
            count += out.samples
            if count > 320000:
                raise ValueError('duration')
            frames.append(out.to_ndarray().flatten())
    if not count:
        raise ValueError('empty')
    return np.concatenate(frames).astype(np.float32) / 32768.0

def main():
    resource.setrlimit(resource.RLIMIT_CPU, (38, 39))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    if len(sys.argv) != 2 or os.path.getsize(sys.argv[1]) > 2097152:
        raise ValueError('size')
    audio = decode_bounded(sys.argv[1])
    from faster_whisper import WhisperModel
    model = WhisperModel('/opt/jarvis-stt/model', device='cpu', compute_type='int8', cpu_threads=1, num_workers=1, local_files_only=True)
    segments, _ = model.transcribe(audio, language='es', beam_size=1, condition_on_previous_text=False, vad_filter=True)
    text = ' '.join(segment.text.strip() for segment in segments).strip()
    if len(text) > 4000:
        raise ValueError('text')
    print(json.dumps({'text': text}, ensure_ascii=False))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.exit(2)
