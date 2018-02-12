#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Model for the wormbase gene summary table within the mapping worker.

Used to help in summarizing the number of genes, variants, etc. within an interval.

"""
from sqlalchemy.orm import sessionmaker, column_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column,
                        String,
                        Integer,
                        create_engine,
                        func,
                        or_)

db_mapping_worker = create_engine('sqlite:///mapping_worker/genes.db')
Session = sessionmaker(bind=db_mapping_worker)

Base = declarative_base()

class wormbase_gene_summary_m(Base):
    """
        This is a condensed version of the wormbase_gene_m model;
        It is constructed out of convenience and only defines the genes
        (not exons/introns/etc.)
    """
    __tablename__ = 'wormbase_gene_summary'
    id = Column(Integer, primary_key=True)
    chrom = Column(String(7), index=True)
    chrom_num = Column(Integer(), index=True)
    start = Column(Integer(), index=True)
    end = Column(Integer(), index=True)
    locus = Column(String(30), index=True)
    gene_id = Column(String(25), index=True)
    gene_id_type = Column(String(15), index=False)
    sequence_name = Column(String(30), index=True)
    biotype = Column(String(30), nullable=True)
    gene_symbol = column_property(func.coalesce(locus, sequence_name, gene_id))
    arm_or_center = Column(String(12), index=True)

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