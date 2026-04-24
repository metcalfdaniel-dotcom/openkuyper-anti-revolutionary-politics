# Open Dutch WordNet (ODWN)

This directory contains the Open Dutch Wordnet data required by `tools/dutch_wordnet.py`.

## File

- `odwn_orbn_gwg-LMF_1.3.xml` — The ODWN lexicon in LMF format (~148MB uncompressed)

## Why it's not in Git

The XML file is **148MB**, which exceeds GitHub's 100MB-per-file limit. It is listed in `.gitignore`.

## How to obtain it

```bash
cd reference/odwn
curl -L -o odwn_orbn_gwg-LMF_1.3.xml.gz \
  "https://github.com/MartenPostma/OpenDutchWordnet/raw/master/resources/odwn/odwn_orbn_gwg-LMF_1.3.xml.gz"
gunzip odwn_orbn_gwg-LMF_1.3.xml.gz
```

## License

CC BY-SA 4.0 (applies to WordNet data; our code is MIT)

## Citation

```
Marten Postma, Ruben Izquierdo Bevia, and Pick Vossen (2013).
Open Dutch WordNet.
In Proceedings of the Global WordNet Conference (GWC-2013).
```

## Usage

Once the file is present, `tools/dutch_wordnet.py` will automatically parse it:

```python
from tools.dutch_wordnet import DutchWordNet

dwn = DutchWordNet("reference/odwn/odwn_orbn_gwg-LMF_1.3.xml")
senses = dwn.suggest_translation_senses("recht")
```
