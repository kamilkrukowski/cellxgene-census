version development

workflow scatter_generate_embeddings {
    input {
        Directory dataset
        Directory model
        String output_name
        Int parts = 10

        String? docker
    }

    scatter (part in range(parts)) {
        call generate_embeddings {
            input:
            dataset, model, output_name, part, parts, docker
        }
    }

    call merge_embeddings {
        input:
        embeddings_parts = generate_embeddings.embeddings, output_name
    }

    output {
        File embeddings = merge_embeddings.embeddings
    }
}

task generate_embeddings {
    input {
        Directory dataset
        Directory model
        String output_name

        # if part is supplied, process only cells satisfying: soma_joinid % parts == part
        Int? part
        Int parts = 1

        String docker = "699936264352.dkr.ecr.us-west-2.amazonaws.com/mlin-census-scratch:latest"
    }

    String outfile = if part == None then "~{output_name}.tsv" else "~{output_name}.~{part}.tsv"

    command <<<
        set -euo pipefail
        >&2 sha256sum /census-geneformer/*.py
        mkdir hf
        export HF_HOME="$(pwd)/hf"
        export TMPDIR="$HF_HOME"
        python3 /census-geneformer/generate-geneformer-embeddings.py \
            ~{"--part " + part} --parts ~{parts} \
            '~{model}' '~{dataset}' '~{outfile}'
    >>>

    runtime {
        # sizing to g5.2xlarge since EmbExtractor uses only one GPU
        cpu: 8
        memory: "30G"
        gpu: true
        docker: docker
    }

    output {
        File embeddings = outfile
    }
}

task merge_embeddings {
    input {
        Array[File] embeddings_parts
        String output_name

        String docker = "ubuntu:22.04"
    }

    command <<<
        set -euxo pipefail

        # Concatenate the parts (without header)
        while read -r part; do
            tail -n +2 "$part" >> /tmp/embeddings
        done < '~{write_lines(embeddings_parts)}'

        # Sort by the first column (soma_joinid), prepending the header
        head -n 1 '~{embeddings_parts[0]}' > '~{output_name}.tsv'
        sort -k1,1n /tmp/embeddings >> '~{output_name}.tsv'
        pigz '~{output_name}.tsv'
    >>>

    runtime {
        cpu: 4
        memory: "8G"
        docker: docker
    }

    output {
        File embeddings = output_name + ".tsv.gz"
    }
}
