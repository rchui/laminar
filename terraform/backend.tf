terraform {
  backend "s3" {
    bucket  = "rchui-terraform-state-us-west-2"
    key     = "laminar/us-west-2/state.tf"
    profile = "personal"
    region  = "us-west-2"
  }
}
