CD ..
Write-Host "When docker has run an you are at bash inside container, you can run one of these commands:"
Write-Host "python default.py -h"
Write-Host "python default.py -i sites.json -o reports/results.json -r"
Write-Host "python default.py -u https://webperf.se -t 26  -o reports/webperf-se-t-26.json -r"
New-Item -ItemType Directory -Force -Path "$(pwd)\reports\"
docker run -it --mount src="$(pwd)\reports",target=/usr/src/app/reports,type=bind --cap-add=SYS_ADMIN --cpus=".9" --shm-size=3g --rm webperf-runner:latest bash
CD docker