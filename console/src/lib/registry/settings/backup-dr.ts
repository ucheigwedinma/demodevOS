import { registerResource } from "../index";

registerResource({
  key: "backup-dr",
  module: "settings",
  label: "Backup & DR",
  labelPlural: "Backup frequency, region, and disaster recovery configuration",
  endpoint: "/settings/backup-dr/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "backup", label: "Backup" },
    { key: "recovery", label: "Recovery Targets" },
    { key: "failover", label: "Failover Triggers" },
  ],
  formFields: [
    {
      key: "backup_frequency",
      label: "Backup Frequency",
      type: "select",
      options: [
        { value: "hourly", label: "Hourly" },
        { value: "every_6h", label: "Every 6 Hours" },
        { value: "every_12h", label: "Every 12 Hours" },
        { value: "daily", label: "Daily" },
        { value: "weekly", label: "Weekly" },
      ],
      section: "backup",
    },
    {
      key: "backup_region",
      label: "Backup Region",
      type: "select",
      options: [
        { value: "us-east-1", label: "US East 1" },
        { value: "us-west-2", label: "US West 2" },
        { value: "eu-west-1", label: "EU West 1" },
      ],
      section: "backup",
    },
    { key: "rto_minutes", label: "RTO (minutes)", type: "number", section: "recovery" },
    { key: "rpo_minutes", label: "RPO (minutes)", type: "number", section: "recovery" },
    { key: "failover_on_db_failure", label: "Database Failure", type: "boolean", section: "failover" },
    { key: "failover_on_network_outage", label: "Network Outage", type: "boolean", section: "failover" },
    { key: "failover_on_storage_failure", label: "Storage Failure", type: "boolean", section: "failover" },
    { key: "failover_on_app_crash", label: "Application Crash", type: "boolean", section: "failover" },
    { key: "failover_on_manual_trigger", label: "Manual Trigger", type: "boolean", section: "failover" },
  ],
});
