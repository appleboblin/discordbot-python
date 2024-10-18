from mcrcon import MCRcon as r
with r('192.168.2.139', '!FYYh8rDc#2zryw%7Vu') as mcr:
    resp = mcr.command('/stop')
print(resp) #there are 0/20 players online: - This will be different for you.
