# myNHLstats Summary
`myNHLstats` is a python library that has been a pet project for a couple years now. It utilizes the [nhlstats](https://github.com/tomplex/nhlstats) library vreated by tomplex that quickly scrapes the NHL api to collect stats from individual NHL games. Though, I do plan to replace the nhlstats dependency with my own version of an NHL API scraper. After collecting the raw stats and cleaning/maniuplating the data (via the `GameStats.py` script), I then publish the data in interactive plots utilizing `plotly` and `datapane`. Eventually the goal is to be able to use these scripts to provide data and visuals for my own website.

# Examples

### Collecting and cleaning data
Data

Stats can be presented on a single game basis (primary focus so far), or to summarize stats over multiple games. I have primarily been focused on the single game plots, but recently added the functionality to summarize and visualize various stats over the past 5 or more games. [Here](https://datapane.com/u/greg/reports/colorado-avalanche-arizona-coyotes-28-feb-2021/) is an example of the interactive plot produced for a single game. The plots for stats over the prior 5 games are still in development. Specifically, aggregating x/y position data for various stats and then standardizing the events relative to a teams attacking zone has been the biggest problem. Once that is figured out, the data can be presented in a heat map to show where a team is shooting from the most, giving away the puck, or laying checks.



