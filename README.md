# Autopunch

Así verás que no se me olvida fichar.

### Fichar / desfichar
El comando siguiente entra en timenet y ejecuta un marcaje. Si el usuario sale que está trabajando, pulsa el botón de fichar; si es al contrario, pulsa el botón de desfichar.
```
autopunch punch
```
Requiere de variables de entorno ```AUTOPUNCH_TIMENET_USER``` y ```AUTOPUNCH_TIMENET_PASSWORD```.


### Programación dinámica de fichajes
Si quieres is más allá y tener un fichaje programado dinámicamente en GCP, puedes usar el siguiente comando. Esto entra en timenet, mira el número de horas que se espera que trabaje en el día actual, y planifica un Cloud Run de GCP con el comando ```punch``` las 9hs y para las 9+{numero de horas esperadas}.
```
autopunch program
```
Requiere de las variables de antes, más ```GOOGLE_APPLICATION_CREDENTIALS```, ```AUTOPUNCH_GCP_PROJECT_ID```, ```AUTOPUNCH_GCP_JOB_NAME``` y ```AUTOPUNCH_GCP_LOCATION```.

