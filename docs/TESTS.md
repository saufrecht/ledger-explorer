# Test Coverage


```coverage run --branch --source=ledgex -m pytest```


```
coverage report
Name                           Stmts   Miss Branch BrPart  Cover
----------------------------------------------------------------
ledgex/__init__.py                 0      0      0      0   100%
ledgex/app.py                      2      0      0      0   100%
ledgex/apps/__init__.py            0      0      0      0   100%
ledgex/apps/balance_sheet.py      44     44     14      0     0%
ledgex/apps/data_source.py        33     33     12      0     0%
ledgex/apps/explorer.py          107    107     32      0     0%
ledgex/apps/hometab.py             5      5      0      0     0%
ledgex/apps/settings.py           10     10      0      0     0%
ledgex/atree.py                  103     18     36      6    81%
ledgex/index.py                  178    178     98      0     0%
ledgex/loading.py                121     30     43     12    70%
ledgex/params.py                  36     10     12      0    58%
ledgex/utils.py                  309    273     98      0     9%
----------------------------------------------------------------
TOTAL                            948    708    345     18    23%
```