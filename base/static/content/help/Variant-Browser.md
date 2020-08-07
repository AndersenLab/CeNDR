# Variant Browser


<style>

.label {
  width: 80px;
  height: 18px;
  line-height: 12px;
  margin-bottom: 4px;
  display: inline-block;
}

.gt-3 {
    background-color: white;
    border: 1px dotted black;
    color: black;
}

.gt-0.PASS {
  background-color: rgba(194,194,214,1.0);
  border: 1px solid black;
  color: black;
}

.gt-2.PASS {
  background-color: rgba(0, 102, 255,1.0);
  border: 1px solid black;
  color: white;
}

.gt-0:not(.PASS) {
  background-color: rgba(194,194,214,0.25);
  border: 1px dotted black;
  color: black;
}

.gt-2:not(.PASS) {
  background-color: rgba(0, 102, 255,0.25);
  border: 1px dotted black;
  color: black;
}

.het {
  background-color: #ffff00;
  color: black;
}

.gt_set {
  border-right: 1px dotted #b3b3b3;
}

th {
  white-space: nowrap;
}

#variants {
  font-size: 12px;
}

</style>

<a name="standard-tracks"></a>
### Standard Tracks

The `Genes` and `Transcripts` tracks are displayed by default.

##### Genes 

Shows _C. elegans_ genes.

##### Transcripts

Shows transcripts of genes.

##### phyloP

The UCSC genome browser provides a [good explanation](https://genome.ucsc.edu/cgi-bin/hgTrackUi?db=hg19&g=cons46way) of the `phyloP` and `phastCons` tracks and how to interpret them.

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

##### Transposons

The transposons track shows transposon calls from [Laricchia _et al._ 2017](https://andersenlab.org/publications/2017Laricchia.pdf). Each call lists the transposon type and __isotype__.

##### Divergent Regions

...

##### Variants

The variants track shows variation across the species for all isotypes sequenced. Variants are colored according to the legend:

<div class='text-center'>
  <div class="legend-box" style="background-color: #c2c2d6;"></div> <strong>Reference</strong>&nbsp;&nbsp;
  <div class="legend-box" style="background-color: #0066ff;"></div> <strong>Alternate</strong>
</div>

<a name="variant-effects"></a>
### Variant Effects

There are three tracks (LOW, MODERATE, HIGH) that can be used to show variants and their predicted impacts as annotated by [SnpEff](https://snpeff.sourceforge.net/). The tracks are color coded based on severity as follows:

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

<a name='variant-filters'></a>
### Variant filters

Variants displayed on the genome browser are 'soft-filtered', meaning that in some cases they are poor quality. However, we still report them but using a different set of colors to indicate that they should be interpretted carefully. When you hover your mouse over filtered variants on the browser page, the name of the filter will appear as a tooltip.

Examples are listed below

<div class="panel-body">
    <span class="label gt-0 PASS">CB4856</span> - A passing reference variant<br />
    <span class="label gt-2 PASS">DL238</span> - A passing alternative variant<br />
    <span class="label gt-0 mapping_quality min_depth dv_dp het">QX1211</span> - A reference variant<br />
    <span class="label gt-2 mapping_quality min_depth dv_dp het">XZ1516</span> - An alternative variant<br />
    <span class="label gt-1 het">JU1218</span> - A heterozygous variant
</div>


# Annotations

Two types of variant annotations are avaiable.