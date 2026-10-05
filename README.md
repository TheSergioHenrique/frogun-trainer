# frogun-trainer

infinite health cheat for [Frogun](https://store.steampowered.com/app/1575470/Frogun/) on linux

made this bc the game is unfair as fuck and i was 1 step away from breaking my controller. its single player so chill, not bothering anyone

## what do you need to run this program?

- linux + frogun from steam
- python 3
- [scanmem](https://github.com/scanmem/scanmem)
- sudo (to mess with the game memory)

```bash
sudo dnf install scanmem   # fedora
sudo apt install scanmem   # ubuntu/debian
```

## how to use

open the game, go into a level and run:

```bash
python3 frogun_trainer.py
```

it asks how many hearts you have. take damage, type the new number, repeat like 2 or 3 times until it finds it. then pick how many hearts you want locked and thats it

ctrl+c turns it off

**important:** only type the number AFTER the health changed on screen, otherwise it throws away the right address

### options

- `--interval 0.2` how often it rewrites the health
- `--max-matches 5` keeps filtering until this many addresses are left
- `--process Frogun` executable name

## stuff that doesnt work

- if you close the game you have to run it again (the address changes). sometimes it changes when you switch levels too
- falling in a pit/lava still kills you. nothing i can do

## license

MIT, do whatever
