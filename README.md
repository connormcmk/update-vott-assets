# update-vott-assets
A script to enable transferring VoTT assets between machines when using Local File System


# Inspiration
[Feature: Ability to move project source location and maintain asset IDs](https://github.com/microsoft/VoTT/issues/762)

# Usage
```
git clone this-repo && cd this-repo
pipenv install && pipenv shell
python update_vott_assets.py --help
```

# Caveats
Not tested with video files
Has a (click)[https://click.palletsprojects.com/en/7.x/] dependency. Could be replaced with argparse if anyone is a purist.
