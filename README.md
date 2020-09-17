# ledger-explorer
Navigate a hierarchical ledger graphically, all the way down to individual transactions.  This tool's purpose is enabling quick navigation through a graphical view of aggregate data in a pie chart or bar chart, representing tens of thousands of records, to a list of specific transactions.  This seems like a really obvious feature but has been surprisingly (in my limited experienc) rare in off-the-shelf F/OSS interactive visualization tools.  The Plotly Dashboard works very well for this purpose.

![Screenshot](https://raw.githubusercontent.com/saufrecht/ledger-explorer/master/docs/montage.jpg?s=820x838)

# Installation

See [docs/INSTALL.md](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/INSTALL.md)

# Usage

See [docs/USAGE.md](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/USAGE.md)

# Known Bugs
Yes, many.  In particular:

1. Navigating to Settings tab auto-loads new defaults, which it oughtn't, since this means defaults are coded in two places.
   1. If you then navigate back to Data Source tab, these defaults will break the default load.
       1. If you edit the settings before navigating back to Data Source, Data Source will apply the new settings.  But navigating back to Settings will erase your inputs, resetting them to the defaults (which, again, are different from the defaults you get if you never navigate to Settings tab)
1. If no era file is present, clicking the Era selector will cause an error.

# Roadmap

1. Complete unit testing (currently 1% coverage)
1. Verify running in gunicorn
1. Publish somewhere as a free service
1. Implement night mode using Dash's native commands
1. Add ability to import at least 1 public data set, maybe national budget?
   1. Add ability to save and load settings, including data sources.
   1. Improve the UI of Data Source to make it easy to test column name settings and see results.
1. Improve navigation and charting tools

# Contributing

Yes, please.  Questions, requests, better documentation, and patches welcome.
