# MastoInky
Display image posts from a Mastodon personal, hashtag or public timeline on a Raspberry Pi with the Pimoroni Inky Impression
## Prerequisites
You will need a Raspberry Pi (I used a Zero W) and the [Pimoroni Inky Impression 7-colour Eink display](https://shop.pimoroni.com/products/inky-impression-7-3).

## Installation
1. Either use raspi-config to manually enable I2C and SPI, or do the following
```
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
pip3 install inky[rpi,example-depends]
```
2. Install Python libraries
```
pip3 install Mastodon.py
pip3 install pillow
```
3. Download MastoInky to your Pi
```
git clone https://github.com/recantha/MastoInky
cd MastoInky
```
4. Get a Mastodon access token at https://{your mastodon instance}/settings/applications

5. Enter your API credentials in `credentials_example.py` and rename to `credentials.py`

6. If you want to follow an account's timeline, you first have to find the account id
```
python3 search_for_account_id.py
```
and add it to `credentials.py`.

7. At the bottom of `mastoinky.py` uncomment the relevant line for the timeline to use (account, public or hashtag).

8. run
```
python3 mastoinky.py
```
