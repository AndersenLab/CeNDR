from flask import Markup
from base.application import db_2
from base.constants import BAM_URL_PREFIX
from sqlalchemy import or_


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
                        <a href="{BAM_URL_PREFIX}/{self.isotype}.bam">
                            BAM
                        </a>
                        /
                        <a href="{BAM_URL_PREFIX}/{self.isotype}.bam.bai">
                            bai
                        </a>
                   """.strip())
        return url_set


class wormbase_gene_m(db_2.Model):
    __tablename__ = 'wormbase_gene'
    id = db_2.Column(db_2.Integer, primary_key=True)
    seqname = db_2.Column(db_2.String(20), index=True)
    feature = db_2.Column(db_2.String(30), index=True)
    start = db_2.Column(db_2.Integer(), index=True)
    end = db_2.Column(db_2.Integer(), index=True)
    strand = db_2.Column(db_2.String(1))
    frame = db_2.Column(db_2.Integer(), nullable=True)
    gene_id = db_2.Column(db_2.String(), nullable=True)
    gene_biotype = db_2.Column(db_2.String(30), nullable=True)
    locus_name = db_2.Column(db_2.String(30), index=True)
    transcript_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    transcript_biotype = db_2.Column(db_2.String(), index=True)
    exon_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    exon_number = db_2.Column(db_2.Integer(), nullable=True)
    protein_id = db_2.Column(db_2.String(30), nullable=True, index=True)

    @classmethod
    def resolve_gene_id(cls, query):
        """
            query - a locus name or transcript ID
            output - a wormbase gene ID

            Example:
            wormbase_gene_m.resolve_gene_id('pot-2') --> WBGene00010195
        """
        result = cls.query.filter(or_(cls.transcript_id == query, cls.locus_name == query)).first()
        if result:
            return result.gene_id

    def __repr__(self):
        return f"{self.gene_id} [{self.seqname}:{self.start}-{self.end}]"


class homologs_m(db_2.Model):
    id = db_2.Column(db_2.Integer, primary_key=True)
    gene_id = db_2.Column(db_2.String(40), index=True)
    gene_name = db_2.Column(db_2.String(40), index=True)
    homolog_species = db_2.Column(db_2.String(50), index=True)
    homolog_taxon_id = db_2.Column(db_2.Integer, index=True, nullable=True) # If available    
    homolog_gene = db_2.Column(db_2.String(50), index=True)
    homolog_source = db_2.Column(db_2.String(40))
    is_ortholog = db_2.Column(db_2.Boolean(), index=True)

    def is_ortholog(self):
        pass

    def __repr__(self):
        return f"homolog: {self.homologene}"

