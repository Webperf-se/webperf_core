CD ..
Write-Host "When docker has run an you are at bash inside container, you can run one of these commands:"
Write-Host "python default.py -h"
Write-Host "python default.py -i defaults/sites.json -r"
Write-Host "python default.py -u https://webperf.se -t 26 -r"
docker run -it  --cpus="0.9" --shm-size=4g -e MAX_OLD_SPACE_SIZE=7000 --rm webperf-core:latest bash
CD docker