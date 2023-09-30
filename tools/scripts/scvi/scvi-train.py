import cellxgene_census
import tiledbsoma as soma
import torch
import yaml
from cellxgene_census.experimental.pp import highly_variable_genes

import scvi

file = "scvi-config.yaml"

with open(file) as f:
    config = yaml.safe_load(f)

census = cellxgene_census.open_soma()

census_config = config["census"]
experiment_name = census_config["organism"]
obs_value_filter = census_config["obs_query"]

query = census["census_data"][experiment_name].axis_query(
    measurement_name="RNA", obs_query=soma.AxisQuery(value_filter=obs_value_filter)
)

hvg_config = config["hvg"]
top_n_hvg = hvg_config["top_n_hvg"]
hvg_batch = hvg_config["hvg_batch"]
min_genes = hvg_config["min_genes"]

hvgs_df = highly_variable_genes(query, n_top_genes=top_n_hvg, batch_key=hvg_batch)

hv = hvgs_df.highly_variable
hv_idx = hv[hv == True].index  # fmt: skip

query = census["census_data"][experiment_name].axis_query(
    measurement_name="RNA",
    obs_query=soma.AxisQuery(value_filter=obs_value_filter),
    var_query=soma.AxisQuery(coords=(list(hv_idx),)),
)
ad = query.to_anndata(X_name="raw")

ad.obs["batch"] = ad.obs["dataset_id"] + ad.obs["assay"] + ad.obs["suspension_type"] + ad.obs["donor_id"]

# scvi settings
scvi.settings.seed = 0
print("Last run with scvi-tools version:", scvi.__version__)

scvi.model.SCVI.setup_anndata(ad, batch_key="batch")

model_config = config["model"]
n_hidden = model_config["n_hidden"]
n_latent = model_config["n_latent"]
n_layers = model_config["n_layers"]
dropout_rate = model_config["dropout_rate"]

model = scvi.model.SCVI(ad, n_layers=n_layers, n_latent=n_latent, gene_likelihood="nb")

train_config = config["train"]
max_epochs = train_config["max_epochs"]
batch_size = train_config["batch_size"]
train_size = train_config["train_size"]
early_stopping = train_config["early_stopping"]
devices = train_config["devices"]

trainer_config = train_config["trainer"]

training_plan_config = config["training_plan"]

scvi.settings.dl_num_workers = train_config["num_workers"]

model.train(
    max_epochs=max_epochs,
    batch_size=batch_size,
    train_size=train_size,
    early_stopping=early_stopping,
    plan_kwargs=training_plan_config,
    trainer_kwargs=trainer_config,
    strategy="ddp_find_unused_parameters_true",
    devices=devices,
)

torch.save(model.module.state_dict(), "scvi.model")
