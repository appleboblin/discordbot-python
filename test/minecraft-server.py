import minestat

ms = minestat.MineStat('192.168.2.139')
print('Minecraft server status of %s' % (ms.address))
if ms.online:
  print('Server is online running version %s with %s out of %s players.' % (ms.version, ms.current_players, ms.max_players))
  print('Message of the day: %s' % ms.motd)
  print('Message of the day without formatting: %s' % ms.stripped_motd)
  print('Latency: %sms' % ms.latency)
  print('Connected using protocol: %s' % ms.slp_protocol)
else:
  print('Server is offline!')