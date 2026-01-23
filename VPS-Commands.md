Remove the old image explicitly, then rebuild
cd /opt/l9
git pull origin main
docker compose stop l9-api
docker compose rm -f l9-api
docker rmi l9-l9-api          # removes the old imagedocker compose build l9-api
docker compose up -d l9-api
sleep 10
docker compose logs l9-api --tail=50
====

cd /opt/l9
align VPS to main
git fetch origin
git reset --hard origin/main

# 4) Rebuild API image and restart container
docker compose build --no-cache l9-api
docker compose up -d l9-api
sleep 10
docker compose logs l9-api --tail=40