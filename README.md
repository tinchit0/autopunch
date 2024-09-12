# Autopunch

Así verás que no se me olvida fichar

Fichar/desfichar. Entra en timenet, si dice que no estoy trabajando ficha, y si sí estoy trabajando, desficha.
```
docker run autopunch punch
```

Programar fichajes. (GCP auth needed) Entra en timenet, mira el número de horas que se espera que trabaje en el día actual, y planifica un Cloud Run de GCP con el comando de antes para las 9hs y para las 9+{numero de horas esperadas}.
```
docker run --rm -v ./keys:/keys -e GOOGLE_APPLICATION_CREDENTIALS=/keys/key.json autopunch program
```
