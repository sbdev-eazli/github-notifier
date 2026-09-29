# github-notifier

Polls your GitHub notifications with the `gh` CLI and shows new ones as desktop notifications (`notify-send`). Each notification fires only once; seen IDs are stored in `~/.cache/github-notifier/seen.json`.

## Requirements

- Linux desktop with `notify-send` (package `libnotify-bin` on Debian/Ubuntu, `libnotify` on Fedora/Arch)
- Python 3.8+ (standard library only)
- [GitHub CLI](https://cli.github.com/) (`gh`), authenticated: `gh auth login`

## Setup

```bash
git clone https://github.com/sbdev-eazli/github-notifier.git ~/github-notifier
cd ~/github-notifier
gh auth status
python3 notifier.py --once   # one check to confirm it works
```

## Usage

```bash
python3 notifier.py                                   # poll every 60s, all notification types
python3 notifier.py --interval 120                    # poll every 2 minutes
python3 notifier.py --reason review_requested,mention # only these reasons
python3 notifier.py --once                            # single check, then exit
```

Reasons: `review_requested`, `comment`, `mention`, `assign`, `author`, `state_change`, `team_mention`, `subscribed` (and any other reason GitHub returns).

The first run marks every existing notification as seen and fires for all of them. After that, only new ones fire.

## Run as a systemd service

Run it as a **user** service tied to your graphical session. That way it has your `gh` login and can reach the desktop to show notifications.

1. Create `~/.config/systemd/user/github-notifier.service`:

   ```ini
   [Unit]
   Description=GitHub desktop notifier
   After=graphical-session.target network-online.target
   PartOf=graphical-session.target

   [Service]
   Type=simple
   ExecStart=/usr/bin/python3 -u %h/github-notifier/notifier.py --interval 60
   Restart=on-failure
   RestartSec=30

   [Install]
   WantedBy=graphical-session.target
   ```

   Change the path if you cloned it somewhere other than `~/github-notifier`, and add `--reason ...` to `ExecStart` to filter. `%h` is your home directory.

2. Enable and start it:

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now github-notifier.service
   ```

Useful commands:

```bash
systemctl --user status github-notifier
journalctl --user -u github-notifier -f      # each notification is also logged with its URL
systemctl --user restart github-notifier
systemctl --user disable --now github-notifier
```

### Troubleshooting

- **No popups but the service is running:** your desktop may not start `graphical-session.target` (some window managers don't). Change `WantedBy=` to `default.target`, then run `systemctl --user import-environment DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS` from your session startup.
- **`gh api call failed` in the logs:** run `gh auth status` as the same user. If `gh` isn't in `/usr/bin` or `/usr/local/bin`, add `Environment=PATH=/path/to/gh/dir:/usr/bin:/bin` under `[Service]`.
- **Replay everything:** stop the service and delete `~/.cache/github-notifier/seen.json`.
