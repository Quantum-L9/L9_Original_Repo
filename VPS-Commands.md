Remove the old image explicitly, then rebuild
cd /opt/l9git pull origin maindocker compose stop l9-apidocker compose rm -f l9-apidocker rmi l9-l9-api          # removes the old imagedocker compose build l9-apidocker compose up -d l9-api

