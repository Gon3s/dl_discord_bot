# Discord Bot for debrid and download movies and series

A Bot discord to debrid and download movies and series with the command 
```!download <url>```

## Setup
Bot requires Python 3 to run

### Install dependencies
```pip install -r requirements.txt```

### Setup config
```.env
DISCORD_TOKEN=your_discord_token
DISCORD_GUILD=your_discord_guild

ALLDEBRID_API_KEY=your_alldebrid_api_key

DOWNLOAD_PATH=your_download_path

WAWACITY_URL=https://www.wawacity.city/
```

## How to run
The bot can be run with the following command:
```python bot.py```

## Create a service

Create a file called `my_bot` :

```sh
nano /etc/systemd/system/my_bot.service
```

Add this :

```sh
[Unit]
Description=My Python Discord Bot
After=multi-user.target

[Service]
WorkingDirectory={{path from the bot script}}
User={{ your user }}

ExecStart=/bin/bash -c "source venv/bin/activate && python bot.py" 

# This will restart your bot if your bot doesn't return a 0 exit code
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Reload systemctl deamon

```sh
systemctl daemon-reload
```

Command to start

```sh
systemctl start my_bot
```

Command to stop

```sh
systemctl stop my_bot
```

Command to restart

```sh
systemctl restart my_bot
```

Command to start when your server start

```sh
systemctl enable my_bot
```

Command to revoke that you would do

```sh
systemctl disable my_bot
```

## Contribution
You can always pull request to this repo, if you report or fix a bug.