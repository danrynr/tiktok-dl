import argparse
import requests
import datetime
import pytz
import subprocess
import os
import time
import random

from fake_useragent import UserAgent
from dotenv import load_dotenv
from rich import print

parser = argparse.ArgumentParser(description='TikTok Downloader')
parser.add_argument('url', default='@tiktok', metavar='str', nargs='*', type=str, help='Accepting: (post URL, account URL, post ID, account name. Ex. @ive.official)')
parser.add_argument('-d', default='~/Tiktok', metavar='str', type=str, help='Download directory')
parser.add_argument('-n', default='33', type=str, help='Number of videos to download (default: 33)')
parser.add_argument('-a', metavar='str', type=str, help='Text file containing TikTok URLs')
args = parser.parse_args()

api = 'https://tiktok-video-no-watermark2.p.rapidapi.com' # RapidAPI

load_dotenv('.tiktok-dl.env')


def get_user_agent():
    ua = UserAgent(
            browsers=['firefox', 'chrome'],
            os=['windows', 'macos'], 
            min_percentage=1.3).random
    return ua


def req(url):
    url = url.strip()
    data = {
        'url': url,
        'hd': 1
    }

    headers = {
        'User-Agent': get_user_agent(),
        'X-RapidAPI-Key': os.getenv('TT_RAPIDAPI_KEY'),
        'X-RapidAPI-Host': 'tiktok-video-no-watermark2.p.rapidapi.com',
    }

    # print(data)

    r = requests.get(api, params=data, headers=headers)
    
    if r.json()['code'] == -1:
        print('---------------------------------------')
        print(f'Retrying {url}...')
        time.sleep(random.uniform(1, 60))
        return False
    else:
        # print(r.json())
        download(r.json())
        return True


def req_retry(url):
    while True:
        if req(url):
            break


def download(json_data):
    post_id = json_data['data']['id']
    caption = json_data['data']['title']
    hdvid_url = json_data['data']['hdplay']
    author = json_data['data']['author']['unique_id']
    raw_date = json_data['data']['create_time']
    video_url = f"https://www.tiktok.com/@{json_data['data']['author']['unique_id']}/video/{json_data['data']['id']}"
    raw_date = datetime.datetime.fromtimestamp(raw_date)
    post_date = raw_date.astimezone(pytz.timezone('Asia/Seoul')).strftime('%y%m%d')
    date_time = raw_date.strftime('%Y-%m-%d %H:%M:%S')

    dir = ''

    if args.d:
        dir = os.path.join(args.d, author)
        if not os.path.exists(dir):
            os.makedirs(dir)
    else:
        dir = os.path.join(os.getcwd(), author)

    orig_filename = f'{post_id}.mp4'

    print('---------------------------------------')
    print(f'[italic red]Video {post_id} by [blue]{author}[/blue] on {post_date}[/italic red]')
    
    if os.path.exists(os.path.join(dir, f'{author}.txt')):
        with open(os.path.join(dir, f'{author}.txt'), 'r') as f:
            if post_id in f.read():
                print(f'{post_id} already downloaded!')
                return
    else:
        with open(os.path.join(dir, f'{author}.txt'), 'w'):
            pass

    print(f'[blue]Caption: [/blue]{caption}')
    print(f'[green]Downloading {orig_filename}...[/green]')
    subprocess.run(['yt-dlp', '--quiet', '--ignore-config',
                    '-P', dir, 
                    '-o', f'{orig_filename}',
                    hdvid_url])
    print(f'[italic red]{orig_filename} downloaded![/italic red]')
      
    print(f'[italic yellow]Converting {orig_filename} to {post_date} - {post_id}.mp4...[/italic yellow]')
    if os.path.exists(os.path.join(dir, orig_filename)):
        filename = f'{post_date} - {post_id}.mp4'
        file_location = os.path.join(dir, orig_filename)
        finalname = os.path.join(dir, filename)

        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                        '-i', f'{file_location}',
                        '-c', 'copy',
                        '-movflags', 'use_metadata_tags',
                        '-metadata', f'url={video_url}',
                        '-metadata', f'title={caption}', 
                        '-n',    
                        f'{finalname}'])
        os.remove(os.path.join(dir, orig_filename))
        print(f'[italic white]{filename} created![/italic white]')

        print(f'[italic cyan]Set modify date {filename}...[/italic cyan]')
        subprocess.run(['exiftool', '-q', '-overwrite_original', 
                        f'{finalname}', 
                        f'-FileModifyDate="{date_time}"'])
        
        with open(os.path.join(dir, f'{author}.txt'), 'a') as f:
            f.write(f'{post_id}\n')
    


def page_parser(url):
    headers = {
        'user-agent': get_user_agent(),
        'X-RapidAPI-Key': os.getenv('TT_RAPIDAPI_KEY'),
        'X-RapidAPI-Host': 'tiktok-video-no-watermark2.p.rapidapi.com',
    }

    posts_api = api + '/user/posts'

    data = {
        'url': url,
        'count': args.n,
        'cursor': 0,
        'web': 1,
        'unique_id': url
    }
    r = requests.get(posts_api, params=data, headers=headers)

    for posts in r.json()['data']['videos']:
        req_retry(posts['video_id'])


def main():
    try:
        if args.a:
            with open(args.a) as f:
                for url in f.readlines():
                    req_retry(url)
        elif args.url:
            if isinstance(args.url, list):
                urls = args.url
            elif isinstance(args.url, str):
                urls = [args.url]

            for url in urls:
                if 'video' in url:
                    req_retry(url)
                elif '@' in url:
                    page_parser(url)
                else:
                    req_retry(url)
        else:
            print('Please enter a TikTok URL (Account page, post url, or just the id')
            print('You can also use -a to specify a text file containing TikTok URLs')
    except KeyboardInterrupt:
        print("\r", end="")
        print("KeyboardInterrupt detected. Exiting gracefully.")
        
    
if __name__ == '__main__':
    main()