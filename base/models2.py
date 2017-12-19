from base.application import db_2


class strain_m(db_2.Model):
    __tablename__ = "strain"
    strain = db_2.Column(db_2.String(25), primary_key=True)
    reference_strain = db_2.Column(db_2.Boolean(), index=True)
    isotype = db_2.Column(db_2.String(25), index=True, nullable=True)
    previous_names = db_2.Column(db_2.String(100), nullable=True)
    source_lab = db_2.Column(db_2.String(), nullable=True)
    release = db_2.Column(db_2.Integer(), nullable=False, index=True)
    latitude = db_2.Column(db_2.Numeric(), nullable=True)
    longitude = db_2.Column(db_2.Numeric(), nullable=True)
    elevation = db_2.Column(db_2.Numeric(), nullable=True)
    landscape = db_2.Column(db_2.String(), nullable=True)
    substrate = db_2.Column(db_2.String(), nullable=True)
    photo = db_2.Column(db_2.String(), nullable=True)
    isolated_by = db_2.Column(db_2.String(), nullable=True)
    sampled_by = db_2.Column(db_2.String(), nullable=True)
    isolation_date = db_2.Column(db_2.Date(), nullable=True)
    isolation_date_comment = db_2.Column(db_2.String(), nullable=True)
    notes = db_2.Column(db_2.String(), nullable=True)
    sets = db_2.Column(db_2.String(), nullable=True)


class wormbase_gene_m(db_2.Model):
    __tablename__ = 'wormbase_gene'
    id = db_2.Column(db_2.Integer, primary_key=True)
    seqname = db_2.Column(db_2.String(20), index=True)
    feature = db_2.Column(db_2.String(30), index=True)
    start = db_2.Column(db_2.Integer())
    end = db_2.Column(db_2.Integer())
    strand = db_2.Column(db_2.String(1))
    frame = db_2.Column(db_2.Integer(), nullable=True)
    gene_id = db_2.Column(db_2.String(), nullable=True)
    gene_biotype = db_2.Column(db_2.String(30), nullable=True)
    transcript_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    transcript_biotype = db_2.Column(db_2.String(), index=True)
    exon_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    exon_number = db_2.Column(db_2.Integer(), nullable=True)
    protein_id = db_2.Column(db_2.String(30), nullable=True, index=True)

    def __repr__(self):
        return f"{self.name} [{self.chrom}:{self.start}-{self.end}]"

"""
class wb_gene(Model):
    CHROM = db_2.Column(db_2.String(), index = True, max_length = 5)
    start = IntegerField(index = True)
    end = IntegerField(index = True)
    Name = db_2.Column(db_2.String(), index = True)
    sequence_name = db_2.Column(db_2.String(), index = True)
    biotype = db_2.Column(db_2.String(), index = True)
    locus = db_2.Column(db_2.String(), index = True, default = None, null = True)

    class Meta:
        database = db

class homologene(Model):
    HID = IntegerField(index=True)
    taxon_id = IntegerField(index=True)
    gene_id = IntegerField(index=True) # entrez
    gene_symbol = db_2.Column(db_2.String(), index=True)
    protein_gi = IntegerField(index=True)
    protein_accession = db_2.Column(db_2.String(), index=True)
    species = db_2.Column(db_2.String(), index=True)
    ce_gene_name = db_2.Column(db_2.String(), default=False)
    class Meta:
        database = db

class wb_orthologs(Model):
    wbid = db_2.Column(db_2.String(), index=True)
    ce_gene_name = db_2.Column(db_2.String(), index=True)
    species = db_2.Column(db_2.String(), index=True)
    ortholog = db_2.Column(db_2.String(), index=True)
    gene_symbol = db_2.Column(db_2.String(), index=True)
    method = db_2.Column(db_2.String(), index=True) # Method used to assign ortholog
    class Meta:
        database = db
"""