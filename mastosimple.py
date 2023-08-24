#!/usr/bin/env python3

# MastoInky
# Display image posts from a Mastodon personal, hashtag or public timeline on a Raspberry Pi with the Pimoroni Inky Developer E Ink
# by AxWax (@axwax@fosstodon.org)
# Enter your API credentials in credentials_example.py and rename to credentials.py
# Robot_Font by Fortress Tech at https://www.dafont.com/robot-2.font

import random
import signal
from urllib.request import urlopen

import inky.inky_uc8159 as inky
import RPi.GPIO as GPIO
from inky.auto import auto
from mastodon import Mastodon
from PIL import Image, ImageColor, ImageDraw, ImageFont

from credentials import access_token, api_base_url
from accounts import account_ids

from gpiozero import Button
from time import sleep

import sys
import os

# change working directory to script path
#os.chdir(os.path.dirname(sys.argv[0]))

# configuration

# size and position of the (cropped square) thumbnail
thumb_width = 200
thumb_x = 110
thumb_y = 125

# size, position and font of the text in the speech bubble
text_x = 245
text_y = 77
text_w = 340
text_h = 110
font_name = 'Robot_Font.otf'

# image to be placed in front of other layers - should be placed in img folder
foreground_img = 'projector.png'

post_id = 0
img_id = 0

# set up buttons
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(PIN_INTERRUPT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialise Mastodon
mastodon = Mastodon(
    access_token = access_token,
    api_base_url = api_base_url
)

# Set up InkyDev first to power on the display
#inkydev = InkyDev()

# Set up the Inky Display
#display = inky.Inky((600, 448))

display = auto()
print("Screen colours: {}".format(display.colour))
print("Screen resolution: {}".format(display.resolution))

screen_width, screen_height = display.resolution
thumb_width = screen_width
thumb_x = 0
thumb_y = 0

# Functions

# wrap text even for variable-width fonts
# by Chris Collett at https://stackoverflow.com/a/67203353
def get_wrapped_text(text: str, font: ImageFont.ImageFont, line_length: int):
        lines = ['']
        for word in text.split():
            line = f'{lines[-1]} {word}'.strip()
            if font.getlength(line) <= line_length:
                lines[-1] = line
            else:
                lines.append(word)
        return '\n'.join(lines)

# find the maximum font size for text to be rendered within the specified rectangle
def find_font_size(the_text, the_font, the_canvas, textbox_width, textbox_height):
    for size in range(20, 1, -1): # we start with font size 20 and make it smaller until it fits
        fo = the_font.font_variant(size=size)      
        wrapped_text = get_wrapped_text(the_text,fo,textbox_width)
        left, top , right ,bottom = the_canvas.multiline_textbbox((0,0), wrapped_text, align='center', font = fo)
        text_height = bottom - top
        if text_height < textbox_height:
            break
    return [size, wrapped_text]

# These Pillow image cropping helper function are from
# https://note.nkmk.me/python-pillow-square-circle-thumbnail/
def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))
# crop a square as big as possible
def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

# helper for gradient background by weihanglo https://gist.github.com/weihanglo/1e754ec47fdd683a42fdf6a272904535
def interpolate(f_co, t_co, interval):
    det_co =[(t - f) / interval for f , t in zip(f_co, t_co)]
    for i in range(interval):
        yield [round(f + det * i) for f, det in zip(f_co, det_co)]    

# load the post's image, create a composite image and display it 
def show_image(img, caption = '', media_id=''):

    # load the image, crop it into a square and create a thumb_width * thumb_width pixel thumbnail
    # (given the shape of the TV I'm using now this should probably be less square and more landscape) 
    image = Image.open(img)
    im_thumb = crop_max_square(image).resize((thumb_width, thumb_width),  Image.LANCZOS)
    
    # load the background as the bottom layer
    newImage = Image.new("RGB", (screen_width, screen_height))
    rectangle = ImageDraw.Draw(newImage)

    # create a gradient based on two random colours
    #f_co = ImageColor.getrgb("hsl(" + str(random.randint(0,360)) + ", 100%, 50%)")
    #t_co = ImageColor.getrgb("hsl(" + str(random.randint(0,360)) + ", 100%, 50%)") 
    #for i, color in enumerate(interpolate(f_co, t_co, 600 * 2)):
    #    rectangle.line([(i, 0), (0, i)], tuple(color), width=1)
    
    # now add the thumbnail as the next layer
    newImage.paste(im_thumb, (thumb_x, thumb_y))    

    # load the projector / avatar / speech bubble layer
    #foreground = Image.open('img/' + foreground_img)
    #newImage.paste(foreground, (0, 0),foreground)

    # draw the assembled image 
    draw = ImageDraw.Draw(newImage)

    # load the font and find the largest possible font size for the caption to stay within the speech bubble
    #font = ImageFont.FreeTypeFont(font_name)   
    #font_size, wrapped_text = find_font_size(caption, font, draw, text_w, text_h)
    #font = ImageFont.FreeTypeFont(font_name, font_size)

    #render the text inside the speech bubble
    #draw.multiline_text((text_x, text_y), wrapped_text, font=font, fill=(0, 0, 0), align="center", anchor="mm")

    # send the image to the E Ink display
    display.set_image(newImage)
    display.show()

# grab the Mastodon post's image URL, ALT image description and author name then pass them to the show_image() function 
def show_post_image (post, media_id):
    media_url = post.media_attachments[media_id].preview_url
    media_author = post.account.display_name # or username
    caption = post.media_attachments[media_id].description

    # someone forgot to add their ALT text - let's give them a gentle nudge.
    if not caption:
        caption = "Here could be a beautiful ALT description. Maybe next time?"

    media_desc =  caption + "   wrote " + str(media_author)

    # Let's try to load the image - use 404slide as a fallback when an error occurs
    try:
        the_image = urlopen(media_url)
        show_image(the_image, media_desc, media_id)
    except:
        the_image = 'img/404slide.png'
        show_image(the_image, media_desc, media_id)

max_accounts = len(account_ids)-1
max_requested_posts = 20

def trig_account():
    global trigger_first_post, trigger_account_change, trigger_post_change

    print("Account trigger fired")
    trigger_first_post = True
    trigger_account_change = True
    trigger_post_change = True

def trig_post():
    global trigger_post_change

    print("Post trigger fired")
    trigger_post_change = True

button_A = Button(5)
button_B = Button(6)

button_A.when_pressed = trig_account
button_B.when_pressed = trig_post

# load posts with media attachments from a timeline
# currently only your personal timeline, a hashtag's timeline and the public / federated timeline allow to limit posts to only_media,
# so to get images from lists or the local timeline you would have to filter out posts without media yourself first...

# uncomment the relevant line
#latest_media_post = mastodon.timeline_public(only_media=True, limit=max_posts) # get images from the public timeline / federated feed
#latest_media_post = mastodon.timeline_hashtag('mastogoats', limit = max_posts, only_media = True) # all posts from a certain hashtag

trigger_account_change = True
trigger_post_change = True
trigger_first_post = True

current_account_no = -1
current_post_no = 0

while True:
    if trigger_account_change:
        print("Account change triggered")
        trigger_account_change = False

        current_account_no = current_account_no + 1
        if current_account_no > max_accounts:
            current_account_no = 0

        print("Getting new lot of posts")
        posts = mastodon.account_statuses(id=account_ids[current_account_no], limit=max_requested_posts, only_media=True) # get images from a personal timeline (change account_id in credentials.py)
        max_posts = len(posts)-1 # ensure that your max is equal to the number you managed to get, just in case it's a new account

    if trigger_post_change:
        print("Post change triggered")
        trigger_post_change = False

        if trigger_first_post:
            print("First post triggered")
            current_post = 0
            trigger_first_post = False
        else:
            print("Going to next post")
            current_post = current_post + 1
            if current_post > max_posts:
                print("Posts looped back to start")
                current_post = 0

        print("Showing post {} from account {} on screen".format(current_post, current_account_no))
        show_post_image(posts[current_post], 0)

    sleep(1)
