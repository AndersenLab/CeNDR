from flask import Markup
from base.application import db_2
from base.constants import URLS
from sqlalchemy import or_, func



class metadata_m(db_2.Model):
    """
        Table for storing information about other tables
    """
    __tablename__ = "metadata"
    key = db_2.Column(db_2.String(50), index=True, primary_key=True)
    value = db_2.Column(db_2.String)



class strain_m(db_2.Model):
    __tablename__ = "strain"
    strain = db_2.Column(db_2.String(25), primary_key=True)
    reference_strain = db_2.Column(db_2.Boolean(), index=True)
    isotype = db_2.Column(db_2.String(25), index=True, nullable=True)
    previous_names = db_2.Column(db_2.String(100), nullable=True)
    source_lab = db_2.Column(db_2.String(), nullable=True)
    release = db_2.Column(db_2.Integer(), nullable=False, index=True)
    latitude = db_2.Column(db_2.Float(), nullable=True)
    longitude = db_2.Column(db_2.Float(), nullable=True)
    elevation = db_2.Column(db_2.Float(), nullable=True)
    landscape = db_2.Column(db_2.String(), nullable=True)
    substrate = db_2.Column(db_2.String(), nullable=True)
    photo = db_2.Column(db_2.String(), nullable=True)
    isolated_by = db_2.Column(db_2.String(), nullable=True)
    sampled_by = db_2.Column(db_2.String(), nullable=True)
    isolation_date = db_2.Column(db_2.Date(), nullable=True)
    isolation_date_comment = db_2.Column(db_2.String(), nullable=True)
    notes = db_2.Column(db_2.String(), nullable=True)
    sets = db_2.Column(db_2.String(), nullable=True)

    def __repr__(self):
        return self.strain

    def list_sets(self):
        if self.sets:
            return self.sets.split(",")
        else:
            return []

    def bam_url(self):
        """
            Return bam / bam_index url set
        """

        url_set = Markup(f"""
                        <a href="{URLS.BAM_URL_PREFIX}/{self.isotype}.bam">
                            BAM
                        </a>
                        /
                        <a href="{URLS.BAM_URL_PREFIX}/{self.isotype}.bam.bai">
                            bai
                        </a>
                   """.strip())
        return url_set


class wormbase_gene_m(db_2.Model):
    __tablename__ = 'wormbase_gene'
    id = db_2.Column(db_2.Integer, primary_key=True)
    chrom = db_2.Column(db_2.String(20), index=True)
    chrom_num = db_2.Column(db_2.Integer(), index=True)  # For sorting purposes
    start = db_2.Column(db_2.Integer(), index=True)
    end = db_2.Column(db_2.Integer(), index=True)
    feature = db_2.Column(db_2.String(30), index=True)
    strand = db_2.Column(db_2.String(1))
    frame = db_2.Column(db_2.Integer(), nullable=True)
    gene_id = db_2.Column(db_2.ForeignKey('wormbase_gene_summary_m.gene_id'), nullable=False)
    gene_biotype = db_2.Column(db_2.String(30), nullable=True)
    locus = db_2.Column(db_2.String(30), index=True)
    transcript_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    transcript_biotype = db_2.Column(db_2.String(), index=True)
    exon_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    exon_number = db_2.Column(db_2.Integer(), nullable=True)
    protein_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    arm_or_center = db_2.Column(db_2.String(12), index=True)

    gene_summary = db_2.relationship("wormbase_gene_summary_m", backref='gene_components')


    def __repr__(self):
        return f"{self.gene_id}:{self.feature} [{self.seqname}:{self.start}-{self.end}]"


class wormbase_gene_summary_m(db_2.Model):
    """
        This is a condensed version of the wormbase_gene_m model;
        It is constructed out of convenience and only defines the genes
        (not exons/introns/etc.)
    """
    id = db_2.Column(db_2.Integer, primary_key=True)
    chrom = db_2.Column(db_2.String(7), index=True)
    chrom_num = db_2.Column(db_2.Integer(), index=True)
    start = db_2.Column(db_2.Integer(), index=True)
    end = db_2.Column(db_2.Integer(), index=True)
    locus = db_2.Column(db_2.String(30), index=True)
    gene_id = db_2.Column(db_2.String(25), index=True)
    gene_id_type = db_2.Column(db_2.String(15), index=False)
    sequence_name = db_2.Column(db_2.String(30), index=True)
    biotype = db_2.Column(db_2.String(30), nullable=True)
    gene_symbol = db_2.column_property(func.coalesce(locus, sequence_name, gene_id))
    arm_or_center = db_2.Column(db_2.String(12), index=True)

    @classmethod
    def resolve_gene_id(cls, query):
        """
            query - a locus name or transcript ID
            output - a wormbase gene ID

            Example:
            wormbase_gene_m.resolve_gene_id('pot-2') --> WBGene00010195
        """
        result = cls.query.filter(or_(cls.locus == query, cls.sequence_name == query)).first()
        if result:
            return result.gene_id



class homologs_m(db_2.Model):
    """
        The homologs database combines 
    """
    id = db_2.Column(db_2.Integer, primary_key=True)
    gene_id = db_2.Column(db_2.ForeignKey('wormbase_gene_summary_m.gene_id'), nullable=False, index=True)
    gene_name = db_2.Column(db_2.String(40), index=True)
    homolog_species = db_2.Column(db_2.String(50), index=True)
    homolog_taxon_id = db_2.Column(db_2.Integer, index=True, nullable=True) # If available    
    homolog_gene = db_2.Column(db_2.String(50), index=True)
    homolog_source = db_2.Column(db_2.String(40))

    gene_summary = db_2.relationship("wormbase_gene_summary_m", backref='homologs', lazy='joined')

    def unnest(self):
        """
            Used with the gene API - returns
            an unnested homolog datastructure combined with the wormbase gene summary model.
        """
        self.__dict__.update(self.gene_summary.__dict__)
        self.__dict__['gene_summary'] = None
        return self

    def __repr__(self):
        return f"homolog: {self.gene_name} -- {self.homolog_gene}"


