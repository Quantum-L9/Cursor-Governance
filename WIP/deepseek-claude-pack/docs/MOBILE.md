# Using this from Claude Code on mobile

The DeepSeek routing lives on the machine that runs the `claude` process. The Claude
mobile app is a remote-control client for that host session, so it inherits the routing.

Working topology:

    Claude mobile app -> Remote Control -> Claude Code on your Mac/PC/VPS
                                        -> https://api.deepseek.com/anthropic

What does not work: configuring a custom base URL or DeepSeek key inside the native
mobile app itself.

Recommended: run `scripts/claude-deepseek.sh` on an always-on host with this repo
checked out, enable Remote Control + push notifications, then attach from the phone.
