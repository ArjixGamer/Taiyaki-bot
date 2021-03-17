from discord.ext import tasks, commands
import discord
import json
import os
import asyncio
import options
import math
import re
import time
import datetime as dt


if not os.path.isfile('sites.json'):
    with open('sites.json', 'w') as f:
        json.dump([], f)


if not os.path.isfile('contributors.json'):
    with open('contributors.json', 'w') as f:
        json.dump({}, f)


def get_sites():
    with open('sites.json', 'r') as f:
        return json.load(f)


def request_site(data):
    all_sites = get_sites()
    all_sites.append(data)
    with open('sites.json', 'w') as f:
        json.dump(all_sites, f, indent=4)


def update_site(sitename, new_data):
    all_sites = get_sites()
    new_list = []
    found = False

    for site in all_sites:
        if site['site'].strip().lower() == sitename.strip().lower():
            new_list.append(new_data)
            found = True
            continue
        new_list.append(site)

    with open('sites.json', 'w') as f:
        json.dump(new_list, f, indent=4)

    return found


def remove_site(sitename):
    all_sites = get_sites()
    new_list = []
    found = False

    for site in all_sites:
        if site['site'].strip().lower() == sitename.strip().lower():
            found = True
            continue
        new_list.append(site)

    with open('sites.json', 'w') as f:
        json.dump(new_list, f, indent=4)

    return found


def increment_counter_for_site(sitename, userID):
    all_sites = get_sites()
    new_array = []
    status = True

    for site in all_sites:
        if site['site'] == sitename:
            dat = site
            if str(userID) in dat['voters']:
                new_array.append(dat)
                status = False
                continue
            dat['count'] += 1
            dat['voters'].append(str(userID))
            new_array.append(dat)
            continue
        new_array.append(site)

    with open('sites.json', 'w') as f:
        json.dump(new_array, f, indent=4)
    return status


def get_site(siteName):
    sites = get_sites()
    for site in sites:
        if siteName.strip().lower() == site['site']:
            return site
    return False


def getSuccessEmbed(Msg):
    embed = discord.Embed(color=0x00ff00)
    embed.set_author(name='Success')
    embed.description = Msg
    return embed


def getErrorEmbed(errMsg):
    embed = discord.Embed(color=0xFF0000)
    embed.set_author(name='Error')
    embed.description = errMsg
    return embed


"""
=========================================
    Setup
=========================================
"""
command_prefix = 'u!'
BOT_TOKEN = options.BOT_TOKEN
CHANNEL_IDS = options.REQUEST_CHANNELS


def run(client):
    client.run(BOT_TOKEN)


client = commands.Bot(command_prefix=command_prefix)
client.remove_command('help')

"""
=========================================
    Events
=========================================
"""


@client.event
async def on_ready():
    print('Discord bot is ready.')


"""
=========================================
    Commands
=========================================
"""
commands_ = [
    ['ls',
        'Short for List Sites, as the name suggests, it lists the sites from the request list.'],
    ['request', 'Helps you request a source to be added in Taiyaki.'],
    ['register', 'Registers you as a contributor so that you can have access to contributor only commands.'],
    ['ping', 'Sends the latency of the bot.']
]

commands_contrib = [
    ['claim', 'Using this command you can claim/assign a request to urself.\nThat way other contributors will know not to pick up the same request as you.'],
    ['clear', 'Using this command you can remove a site from your claimed requests list.\nThis way if you dont want to work on a request anymore you can let other people take over.']
]


@client.command()
async def help(ctx):
    embed = discord.Embed(color=0x808080)
    embed.set_author(name='Help')
    for a in commands_:
        embed.add_field(inline=False, name=a[0], value=a[1])
    if is_contributor(str(ctx.author.id)):
        for a in commands_contrib:
            embed.add_field(inline=False, name=a[0], value=a[1])
    embed.add_field(inline=False, name='help',
                    value='Lists all the available commands the bot offers.')
    await ctx.send(embed=embed)


@client.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(client.latency * 1000)}ms')


@client.command(aliases=['req'])
async def request(ctx, *, arguments=''):
    if ctx.channel.id not in CHANNEL_IDS:
        message = 'You can only use this command in the following channels:\n'
        for id_ in CHANNEL_IDS:
            message += '<#{}> '.format(id_)
        await ctx.send(embed=getErrorEmbed(message))
        return
    regex = r"(?<=[-{1,2}|/])([a-zA-Z0-9]*)[ |:|\"]*([\w|.|?|=|&|+| |:|/|\\]*)(?=[ |\"]|$)"
    requestedBy = str(ctx.author.id)
    finds = re.findall(regex, arguments.lower())
    name, language = None, None

    for param, value in finds:
        if param in ['name', 'n']:
            name = value
        elif param in ['l', 'language']:
            language = value

    if name and language:
        all_sites = [[x['site'], x['requested_by']] for x in get_sites()]
        for site, requester in all_sites:
            if requestedBy == requester and name.lower().strip() == site.lower().strip():
                await ctx.send(embed=getErrorEmbed('You can\'t vote for your own request.'))
                return
        if name in [x for x, i in all_sites]:
            res = increment_counter_for_site(name, requestedBy)
            if res:
                await ctx.send(embed=getSuccessEmbed('Site **{}** was already requested, adding a vote to it instead...'.format(name)))
            else:
                await ctx.send(embed=getErrorEmbed('You can\'t vote multiple times for a single request.'))
            return
        request_site({
            'requested_by': requestedBy,
            'site': name,
            'language': language,
            'count': 1,
            'claimed': False,
            'claimed_by': None,
            'voters': []
        })
        await ctx.send(embed=getSuccessEmbed('Successfully requested **{}** *({})*.'.format(name, language.upper())))
    else:
        await ctx.send(embed=getErrorEmbed('Please send the correct arguments.\nExamples:\n\t``--name gogoanime --language en``\n\t\tor\n\t``-n gogoanime -l en``'))


@client.command(aliases=['list-sites', 'ls'])
async def list_sites(ctx, pageNum: int = 1):
    sites = sorted(get_sites(), key=lambda x: x['count'])[::-1]
    pageEmbeds = {}

    total = len(sites)
    perPage = 10
    pages = math.ceil(total/perPage)
    current = 0

    for page in range(1, pages+1):
        embed = discord.Embed(color=0x808080)
        embed.set_author(name='Page {}\t\t\t\t⠀'.format(page))
        for i in range(perPage):
            if current <= total-1:
                tmpVar = sites[current]
                embed.add_field(
                    inline=False,
                    name=f"{current+1}. " + tmpVar['site'],
                    value='Language: {}\nRequested by: {}{}{}'.format(
                        tmpVar['language'], f"<@{tmpVar['requested_by']}>",
                        '' if not tmpVar['claimed'] else (
                            f"\nClaimed by: <@{tmpVar['claimed_by']}>"),
                        '' if tmpVar['count'] == 1 else f"\nVotes: {tmpVar['count']}"
                    )
                )
            current += 1
        if page < pages:
            embed.set_footer(
                text=f'Use "u!ls {page+1}" to go to the next page!')
        pageEmbeds[page] = embed

    if pageNum in pageEmbeds:
        await ctx.send(embed=pageEmbeds[pageNum])
    else:
        if pages == 0:
            await ctx.send(embed=getErrorEmbed('No requests were found.\nUse u!request to submit a request.'))
            return
        await ctx.send(embed=getErrorEmbed('Page out of index.\nThere are a total of {} pages.'.format(pages)))


"""
=========================================
    Contributors
=========================================
"""


def get_contributors():
    with open('contributors.json', 'r') as f:
        return json.load(f)


def save_contributors(data):
    with open('contributors.json', 'w') as f:
        json.dump(data, f, indent=4)


def is_contributor(id_):
    with open('contributors.json', 'r') as f:
        if str(id_) in json.load(f):
            return True
    return False


def add_contributor(user_id):
    regTime = time.time()
    contribs = get_contributors()
    if str(user_id) in contribs:
        return False
    contribs[str(user_id)] = {
        'points': 0,
        'sites_added': 0,
        'quota': [],
        'time': time.time()
    }
    save_contributors(contribs)
    return True


def remove_claim(siteName):
    all_contribs = get_contributors()
    site = get_site(siteName)
    site['claimed'] = False
    site['claimed_by'] = None

    for contrib in all_contribs:
        if siteName.lower().strip() in all_contribs[contrib]['quota']:
            all_contribs[contrib]['quota'].remove(siteName.lower().strip())

    update_site(siteName, site)
    save_contributors(all_contribs)


def award_for_request(siteName):
    all_contribs = get_contributors()

    for contrib in all_contribs:
        if siteName.lower().strip() in all_contribs[contrib]['quota']:
            all_contribs[contrib]['quota'].remove(siteName.lower().strip())
            all_contribs[contrib]['sites_added'] += 1
            all_contribs[contrib]['points'] = all_contribs[contrib]['sites_added'] * 10

    remove_site(siteName)
    save_contributors(all_contribs)


def get_contributor(user_id):
    contribs = get_contributors()
    if not is_contributor(user_id):
        return False
    return contribs[str(user_id)]


def update_contributor_quota(user_id, quota):
    contribs = get_contributors()
    if not is_contributor(user_id):
        return
    contribs[str(user_id)]['quota'] = quota

    with open('contributors.json', 'w') as f:
        json.dump(contribs, f, indent=4)


def claim_site_as_contributor(sitename, contributor):
    all_sites = get_sites()
    new_array = []

    for site in all_sites:
        if site['site'] == sitename.lower().strip():
            dat = site
            dat['claimed'] = True
            dat['claimed_by'] = contributor
            new_array.append(dat)
            continue
        new_array.append(site)

    with open('sites.json', 'w') as f:
        json.dump(new_array, f, indent=4)


@client.command()
async def register(ctx):
    if is_contributor(ctx.author.id):
        await ctx.send(embed=getErrorEmbed('You are already registered in the bot as a contributor.'))
        return
    status = add_contributor(ctx.author.id)
    if status:
        await ctx.send(embed=getSuccessEmbed('Successfully registered you as a contributor.\nContribute to the app to get contribution points, for now they are nothing more than reputation points.'))


@client.command()
async def status(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    if not is_contributor(user.id):
        await ctx.send(embed=getErrorEmbed('There are no stats available for this user, reason being that user is not registered.'))
        return
    contributor = get_contributor(user.id)
    embed = discord.Embed(color=0x808080)
    embed.add_field(inline=False, name='Status',
                    value='Viewing stats for <@{}>'.format(user.id))
    embed.add_field(inline=False, name='Contributor since:', value=dt.datetime.utcfromtimestamp(
        contributor['time']).strftime("%Y/%m/%d"))
    embed.add_field(inline=False, name='Points',
                    value=contributor['points'])
    embed.add_field(inline=False, name='Sites Added',
                    value=contributor['sites_added'])
    if contributor['quota']:
        embed.add_field(inline=False, name='Working on',
                        value=' | '.join(contributor['quota']))
    await ctx.send(embed=embed)


@client.command()
async def claim(ctx, *, siteName):
    if not is_contributor(ctx.author.id):
        await ctx.send(embed=getErrorEmbed('You are not registered in the bot as a contributor.\nTo register use u!register'))
        return
    site = get_site(siteName)
    if not site:
        await ctx.send(embed=getErrorEmbed('**404**:\nRequest not found.'))
        return
    before = get_sites()
    claim_site_as_contributor(siteName.lower().strip(), str(ctx.author.id))
    after = get_sites()
    quota = get_contributor(str(ctx.author.id))['quota']
    if before != after and quota != False:
        quota.append(siteName.lower().strip())
        update_contributor_quota(str(ctx.author.id), quota)
        await ctx.send(embed=getSuccessEmbed('You have successfuly claimed this request.\nComplete it to gain contrib points.'))


@client.command()
async def clear(ctx, *, siteName):
    if not is_contributor(ctx.author.id):
        await ctx.send(embed=getErrorEmbed('You are not registered in the bot as a contributor.\nTo register use u!register'))
        return

    req = get_site(siteName)
    if not req:
        await ctx.send(embed=getErrorEmbed('No such site was requested.'))
        return
    if ctx.message.author.guild_permissions.administrator:
        remove_claim(siteName)
        await ctx.send(embed=getSuccessEmbed('Successfully cleared this site of any claim.'))
    elif req['claimed'] and req['claimed_by'] == str(ctx.author.id):
        remove_claim(siteName)
        await ctx.send(embed=getSuccessEmbed('You successfully dropped your claim for this request.'))
    else:
        await ctx.send(embed=getErrorEmbed(
            ('Possible problems:\n1) You are not allowed to use this command.\n2) No such site is claimed by any contributor.')))


@client.command()
async def checkout(ctx, *, siteName):
    if str(ctx.author.id) != "246755970858876930":
        await ctx.send(embed=getErrorEmbed('Only Admins can use this command.'))
        return

    req = get_site(siteName)
    if not req:
        await ctx.send(embed=getErrorEmbed('No such site was requested.'))
        return
    if not req['claimed']:
        await ctx.send(embed=getErrorEmbed('Can\'t award points for this request as it was not claimed by any contributor.'))
        return

    award_for_request(siteName)

    await ctx.send(embed=getSuccessEmbed('Congratulations to <@{}> for adding {}!'.format(req['claimed_by'], req['site'])))

if __name__ == '__main__':
    run(client)
