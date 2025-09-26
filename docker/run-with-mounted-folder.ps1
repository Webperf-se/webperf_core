CD ..
Write-Host "When docker has run an you are at bash inside container, you can run one of these commands:"
Write-Host "python default.py -h"
Write-Host "python default.py -i defaults/sites.json -o reports/results.json -r"
Write-Host "python default.py -u https://webperf.se -t 26  -o reports/webperf-se-t-26.json -r"
New-Item -ItemType Directory -Force -Path "$(pwd)\reports\"
docker run -it --mount src="$(pwd)\reports",target=/usr/src/runner/reports,type=bind --cpus="0.9" --shm-size=4g -e MAX_OLD_SPACE_SIZE=7000 --rm webperf-core:latest bash
CD docker