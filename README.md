# Autopunch

Así verás que no se me olvida fichar.

### Fichar / desfichar
El comando siguiente entra en timenet y ejecuta un marcaje. Si el usuario sale que está trabajando, pulsa el botón de fichar; si es al contrario, pulsa el botón de desfichar.
```
autopunch punch
```
Requiere de variables de entorno ```AUTOPUNCH_TIMENET_USER``` y ```AUTOPUNCH_TIMENET_PASSWORD```.


### Programación dinámica de fichajes
Si quieres ir más allá y tener los fichajes de hoy programados automáticamente, puedes usar el siguiente comando. Esto entra en timenet, mira el número de horas que se espera que trabajes en el día actual, y programa un ```punch``` a las 9h y otro a las 9+{número de horas esperadas} (con parada para comer si el día es largo).
```
autopunch program
```
Requiere de las variables de antes. El comando admite ```--infra``` para elegir dónde se programan esos ```punch```:

- ```--infra at``` (por defecto): usa el comando ```at``` de Unix para programar ejecuciones de un solo uso en la máquina local, a las horas calculadas. Necesitas tener instalado y arrancado el daemon ```atd```:
  ```
  sudo apt install at
  sudo systemctl enable --now atd
  ```
- ```--infra gcp```: reprograma un job de GCP Cloud Scheduler (comportamiento original). Requiere instalar el extra ```gcp``` (```uv sync --extra gcp``` o ```pip install autopunch[gcp]```) y las variables ```GOOGLE_APPLICATION_CREDENTIALS```, ```AUTOPUNCH_GCP_PROJECT_ID```, ```AUTOPUNCH_GCP_JOB_NAME``` y ```AUTOPUNCH_GCP_LOCATION```.

### Disparo diario de `program` con cron (servidor local)
Para que ```autopunch program``` se ejecute cada día a las 2:00 sin depender de GCP, añade una línea al crontab del usuario (```crontab -e```):

```
0 2 * * * . /etc/autopunch/autopunch.env && /usr/local/bin/autopunch program >> /var/log/autopunch/program.log 2>&1
```

Ajusta ```/usr/local/bin/autopunch``` a donde tengas instalado el comando (`which autopunch`), y crea antes el fichero de entorno y el directorio de logs:
```
sudo mkdir -p /etc/autopunch /var/log/autopunch
sudo chown $USER /var/log/autopunch
sudo tee /etc/autopunch/autopunch.env <<'EOF'
AUTOPUNCH_TIMENET_USER=
AUTOPUNCH_TIMENET_PASSWORD=
EOF
sudo chmod 600 /etc/autopunch/autopunch.env
sudo $EDITOR /etc/autopunch/autopunch.env   # rellena las dos variables
```

El `. /etc/autopunch/autopunch.env &&` al inicio de la línea de cron es importante: sin él, cron ejecuta el comando con un entorno mínimo (sin tus variables) y además manda cualquier output por correo local en vez de a un fichero, igual que vimos con `at`. Como `at` hereda el entorno del proceso que lo invoca, los `punch` programados por `autopunch program` también verán esas variables sin configuración adicional.

Para revisar o cancelar fichajes ya programados: `atq` lista la cola, `atrm <id>` cancela uno. Para ver el crontab activo: `crontab -l`.

