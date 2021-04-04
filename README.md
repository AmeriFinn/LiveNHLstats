# LiveNHLstats
`myNHLstats` is a Python script/module I've been working on since mid-2019. It utilizes the `nhlstats` python module (a basic python plug-in to the NHL Stats API) to collect game stats and present them in interactive plots utilizing `pandas` and `plotly`. I've started reading up on `Dash` and `Holowviews` which allow me to make more advanced graphics, but this will take time which I don't have a ton of... :(

Stats can be presented on a single game basis (primary focus so far), or to summarize stats over multiple games. I have primarily been focused on the single game plots, but recently added the functionality to summarize and visualize various stats over the past 5 or more games. [Here](https://datapane.com/u/greg/reports/colorado-avalanche-arizona-coyotes-28-feb-2021/) is an example of the interactive plot produced for a single game. The plots for stats over the prior 5 games are still in development. Specifically, aggregating x/y position data for various stats and then standardizing the events relative to a teams attacking zone has been the biggest problem. Once that is figured out, the data can be presented in a heat map to show where a team is shooting from the most, giving away the puck, or laying checks.



