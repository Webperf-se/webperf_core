Write-Host "When docker has run an you are at bash inside container, you can do for example:"
Write-Host "python default.py -u https://webperf.se -t 26 -o reports/webperf-se-t-26.json -r"
docker run -it --cap-add=SYS_ADMIN --cpus=".9" --shm-size=3g --rm webperf-runner:0.0.2 bash