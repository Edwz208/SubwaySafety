import FeatureCard from "./common/FeatureCard"
import DataTable from "./common/DataTable"

const events = [
  {
    id: 1,
    camera_id: 1,
    occurred_at: "2024-06-01T12:00:00Z",
    event_type: "Intrusion",
    video_clip_path: "/path/to/video1.mp4",
    description: "Person detected in restricted area"
  }
]

const columns = [
  {
    key: "camera",
    header: "Camera",
    width: "120px",
    cell: (row) => row.camera_id
  },
  {
    key: "time",
    header: "Time",
    width: "220px",
    cell: (row) => new Date(row.occurred_at).toLocaleString()
  },
  {
    key: "type",
    header: "Event",
    width: "160px",
    cell: (row) => row.event_type
  },
  {
    key: "description",
    header: "Description",
    width: "auto",
    cell: (row) => row.description
  }
]

export default function EventTableCard() {
  return (
    <FeatureCard
      title="Recent Events"
      showHeaderDivider
      className='mt-10'
    >
      <DataTable
        columns={columns}
        rows={events}
        getRowKey={(row) => row.id}
        emptyState="No events detected."
      />
    </FeatureCard>
  )
}