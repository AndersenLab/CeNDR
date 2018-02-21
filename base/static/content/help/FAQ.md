## FAQ 

### How do I run the BAM and CRAM download scripts? 
The BAM and CRAM download scripts require wget. Once you have wget, follow the instructions at the top of the scripts.

#### Mac OS or Linux

__wget__ can be obtained using <a href="https://brew.sh/">homebrew</a> on Mac OSX. Install homebrew, then type:

<pre>
brew install wget
</pre>

#### Windows

Install [Cygwin](https://www.cygwin.com/). Then install the wget package.


### How do I use the API?

The Application Programming Interface (API) can be used to access the CeNDR database and make a variety of queries. The API [documentation](/data/api/docs/) details the types of queries you can make and provides examples in a variety of languages. If you are unfamiliar with APIs and how they work, I recommend taking a look at [this guide](https://sunlightfoundation.com/blog/2015/09/08/what-are-apis-why-they-matter-and-how-to-use-them/). 

R can be used to make queries to the API. See the examples below:

__Fetch a dataframe of strain data__

<pre>
library(jsonlite)
df <- fromJSON("https://elegansvariation.org/api/strain")
</pre>

__Fetch all strains for a given isotype__

<pre>
library(jsonlite)
CB_strains <- fromJSON("https://www.elegansvariation.org/api/strain/isotype/CB4856")
</pre>

### How do I cite CeNDR?

Please use the citation below.

<div class="pub"><div class="pub-img">
            </div><div class="pub-img-small">
            <a href="https://andersenlab.org/publications/2016CookOxford.pdf" class="thumbnail" target="_blank">
            <img src="/static/img/2016CookOxford.thumb.png" alt="2016CookOxford">
            </a>
            </div><strong>CeNDR, the <em> Caenorhabditis elegans</em> natural diversity resource</strong><br />Cook DE, Zdraljevic S, Roberts JP, Andersen EC
                <br>                
                (2016 Oct 3) <em>Nucleic Acids Research</em> [ <a href="https://nar.oxfordjournals.org/content/early/2016/10/03/nar.gkw893.full">Article on Nucleic Acids Research</a> | <a title="Document Object Identifier; Takes you to the Journal Website" href="https://dx.doi.org/10.1093/nar/gkw893" target="_blank">DOI</a> | <a href="https://www.ncbi.nlm.nih.gov/pubmed/27701074" target="_blank">Pubmed</a> ]
                <br /><br />
      </div>

<div class='clearfix'></div>
Or use this bibtex entry
<pre>
@article{cook2016cendr,
  title={CeNDR, the Caenorhabditis elegans natural diversity resource},
  author={Cook, Daniel E and Zdraljevic, Stefan and Roberts, Joshua P and Andersen, Erik C},
  journal={Nucleic acids research},
  volume={45},
  number={D1},
  pages={D650--D657},
  year={2016},
  publisher={Oxford University Press}
}</pre>