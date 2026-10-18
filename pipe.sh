#!/bin/bash
r=$1; n=$2
cd "$(dirname "$0")"; mkdir -p out
python3 render.py $r video r${r}_silent.mp4 > rend$r.log 2>&1 || exit 1
python3 music_gen.py $r >> rend$r.log 2>&1 || exit 1
ffmpeg -y -loglevel error -i r${r}_silent.mp4 -i r${r}_music.wav -c:v copy -af loudnorm=I=-14:TP=-1:LRA=11,aresample=44100 -c:a aac -b:a 192k -shortest -movflags +faststart out/$n.mp4 >> rend$r.log 2>&1 && echo done >> rend$r.log
