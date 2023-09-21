# PlexDLWeb

A simple web UI for downloading media from Plex without the Plex Pass.

![chrome_ZpHRswxRB1](https://github.com/zdimension/plexdlweb/assets/4533568/c085d892-78d6-48ab-8290-55677daaac41)

Uses [Python-PlexAPI](https://github.com/pkkid/python-plexapi) and [NiceGUI](https://github.com/zauberzeug/nicegui).

## Requirements

- Should work on any Linux (tested on Debian 11), may work on Windows
- Python 3.9+

## Features

- [x] Login with Plex account (owner or user)
- [x] Search across an entire Plex server
- [x] Download movies and episodes
- [x] Browse collections, shows, and seasons
- [x] Choose between multiple versions of a media item
- [ ] Provide a torrent download in addition to the direct download (planned)
  - This will probably use an embedded torrent client, and generate a unique torrent file valid for 12 or 24 hours. Useful if your connection is too unstable to download the file through HTTP.
- [ ] Auto-update through Git, like Tautulli (planned)

## Basic setup

You will need your server address (e.g. `http://plex.johndoe.com:32400` or `http://127.0.0.1:32400`) and ID. You can the ID by opening `https://plex.johndoe.com/identity`. You'll get something like this:

```xml
<MediaContainer size="0" claimed="1" machineIdentifier="abcdef123456abcdef123456abcdef123456abcd" version="1.32.5.7516-8f4248874"> </MediaContainer>
```

The ID is the `abcdef123456abcdef123456abcdef123456abcd`.

### Standalone

```bash
git clone https://github.com/zdimension/plexdlweb
cd plexdlweb
pip3 install -r requirements.txt
python3 __main__.py  # will generate a config.json file, edit it and start again
```

### Systemd service

```bash
mkdir /opt/plexdlweb && cd /opt/plexdlweb  # you can change the path here

useradd -d $(pwd) plexdlweb

git clone https://github.com/zdimension/plexdlweb .
chown -R plexdlweb .

sudo -u plexdlweb sh -c "pip3 install -r requirements.txt && python3 __main__.py"
nano config.json  # edit config here
sudo -u plexdlweb python3 __main__.py  # make sure it works before setting up the service

sed -i "s%{PATH}%$(pwd)%g" plexdlweb.service
chown root plexdlweb.service
ln -s "$(realpath plexdlweb.service)" /etc/systemd/system/plexdlweb.service

service plexdlweb start
systemctl enable plexdlweb
```

## Updating

As mentioned, an update system is planned. In the meantime, just `git pull` and restart the service.

## Rationale

Plex is an amazing piece of software. Time isn't free, and Plex Inc. needs money. I paid €120 for the Plex Pass so my friends and family can use my server at its full potential (hardware transcoding, credits skipping, etc).

However, since August 1st, 2022, the server owner having a Plex Pass isn't sufficient for users to be able to download. **Each user** must have the Pass. We're not talking about a *complex* feature, again, like transcoding or credits detection. *Downloading files*. I could do that with Apache 20 years ago with a 10-line httpd.conf file.

My users travel. My users take the train, the plane, and go in a number of different places where they don't have a stable connection, and they need to be able to download files for offline viewing. This is not negociable. And giving an SFTP access is not acceptable, most of my users are not computer-literate.

## License

This project is licensed under the GPLv3 license.
