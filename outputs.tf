output "database_connection_parameter" {
  value = "${aws_ssm_parameter.database_connection.name}"
}

output "sgmkr_name" {
  value = "${aws_sagemaker_notebook_instance.main.id}"
}

output "rds_cluster_name" {
  value = "${aws_rds_cluster.main.cluster_identifier}"
}

output "rds_instance_ids" {
  value = "${aws_rds_cluster_instance.main.*.id}"
}
