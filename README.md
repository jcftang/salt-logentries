# Logentries returner for salt

This returner is a basic plugin to return information from minions to
the Logentries service.

In order to use this returner copy '_returner' to your file_roots on
your salt master.

Add the following configuration lines to your minion or master config
file.

```
logentries.endpoint: data.logentries.com
logentries.port: 10000
logentries.token: 0759e7a8-552c-4f5f-bfa1-c2d4afc94aaa
```

The token can be obtained from the logentries service.

The returner can be tested by executing the following command

```
salt '*' --return logentries cmd.run uptime
```

The output from the cmd.run module will be sent to Logentries.

## Notes

This returner is very naive in how it sends data to logentries, further
work could be done to make it more efficient.
