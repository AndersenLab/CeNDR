## FAQ 

### How do I run the BAM and CRAM download scripts? 
The BAM and CRAM download scripts require wget. Once you have wget, follow the instructions at the top of the scripts.

#### Mac OS or Linux

__wget__ can be obtained using <a href="http://brew.sh/">homebrew</a> on Mac OSX. Install homebrew, then type:

<pre>
brew install wget
</pre>

#### Windows

Install [Cygwin](www.cygwin). Then install the wget package.


### How do I use the API?

The Application Programming Interface (API) can be used to access the CeNDR database and make a variety of queries. The API [documentation](http://docs.elegansvariation.apiary.io/) details the types of queries you can make and provides examples in a variety of languages. If you are unfamiliar with APIs and how they work, I recommend taking a look at [this guide](https://sunlightfoundation.com/blog/2015/09/08/what-are-apis-why-they-matter-and-how-to-use-them/). 

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