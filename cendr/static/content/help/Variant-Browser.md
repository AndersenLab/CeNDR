# Variant Browser

<a name="standard-tracks"></a>
### Standard Tracks

The genome browser provides five tracks.

##### Genes 

Shows _C. elegans_ genes.

##### Transcripts

Shows transcripts of genes.

#### Conservation Tracks

The UCSC genome browser provides a [good explanation](http://genome.ucsc.edu/cgi-bin/hgTrackUi?db=hg19&g=cons46way) of the phyloP and phastCons tracks and how to interpret them.

##### phyloP

phyloP (phylogenetic P-values) are designed to detect lineage-specific selection. Positive scores indicate conserved sites (slower evolution than expected under drift) whereas negative scores indicate acceleration (faster evolution than expected under drift).

* _Caenorhabditis elegans_
* _Caenorhabditis brenneri_
* _Caenorhabditis japonica_
* _Caenorhabditis remanei_
* _Caenorhabditis briggsae_
* _Strongyloides ratti_
* _Onchocerca volvulus_
* _Brugia malayi_


##### phastCons

phastCons scores range from 0-1 and represent the probability that each nucleotide belongs to a conserved element.

##### Variants

The variants track shows variation across the species for all isotypes sequenced. Variants are colored according to the legend:

<div class='text-center'>
  <div class="legend-box" style="background-color: #c2c2d6;"></div> <strong>Reference</strong>&nbsp;&nbsp;
  <div class="legend-box" style="background-color: #0066ff;"></div> <strong>Alternate</strong>
</div>

<a name="variant-effects"></a>
### Variant Effects

There are three tracks (LOW, MODERATE, HIGH) that can be used to show variants and their predicted impacts as annotated by [SnpEff](http://snpeff.sourceforge.net/). The tracks are color coded based on severity as follows:

<div class='text-center'>
  <label><div class="legend-box" style="background-color: #66d866;"> </div> LOW</label>&nbsp;&nbsp;
  <label><div class="legend-box" style="background-color: #ffd33f;"></div> MODERATE</label>
  <label><div class="legend-box" style="background-color: #ff3f3f;"></div> HIGH</label>
</div>


These annotations can be used to assess what functional affects a given variant may have and are grouped into LOW, MODERATE, and HIGH impact variants. More information on variant predictions is available on the [Variant Prediction](/help/Variant-Prediction/) page.

<a name="ind-strains"></a>
### Strain Specific Tracks

The variants for individual isotypes can be viewed by selecting tracks from the strain list:

![strain_selection](/static/img/help/strain_selection.png)

Isotypes can also be filtered using the search box. Like the variant track for the entire species, reference and alternate genotypes are colored as follows:

<div class='text-center'>
  <div class="legend-box" style="background-color: #c2c2d6;"></div> <strong>Reference</strong>&nbsp;&nbsp;
  <div class="legend-box" style="background-color: #0066ff;"></div> <strong>Alternate</strong>
</div>

Missing genotypes are excluded.

