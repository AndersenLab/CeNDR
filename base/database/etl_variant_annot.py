# -*- coding: utf-8 -*-
"""
Loads the Strain Variant Annotated CSV into the SQLite DB

Author: Sam Wachspress
"""
import csv

from sqlalchemy.sql.expression import null

def fetch_strain_variant_annotation_data(sva_fname: str):
  """
      Load strain variant annotation table data:

      CHROM,POS,REF,ALT,CONSEQUENCE,WORMBASE_ID,TRANSCRIPT,BIOTYPE,
      STRAND,AMINO_ACID_CHANGE,DNA_CHANGE,Strains,BLOSUM,Grantham,
      Percent_Protein,GENE,VARIANT_IMPACT,DIVERGENT

  """
  with open(sva_fname) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')

    line_count = -1
    for row in csv_reader:
      if line_count == -1:
        print(f'Column names are {", ".join(row)}')
        line_count += 1
      else:
        line_count += 1
        yield {
          'id': line_count,
          'chrom': row[0],
          'pos': int(row[1]),
          'ref_seq': row[2] if row[2] else None,
          'alt_seq': row[3] if row[3] else None,
          'consequence': row[4] if row[4] else None,
          'gene_id': row[5] if row[6] else None,
          'transcript': row[6] if row[6] else None,
          'biotype': row[7] if row[7] else None,
          'strand': row[8] if row[8] else None,
          'amino_acid_change': row[9] if row[9] else None,
          'dna_change': row[10] if row[10] else None,
          'strains': row[11] if row[11] else None,
          'blosum': int(row[12]) if row[12] else None,
          'grantham': int(row[13]) if row[13] else None,
          'percent_protein': float(row[14]) if row[14] else None,
          'gene': row[15] if row[15] else None,
          'variant_impact': row[16] if row[16] else None,
          'divergent': 1 if row[17] == 'D' else None,
        }

  print(f'Processed {line_count} lines.')
