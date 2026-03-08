import { useQuery } from "@tanstack/react-query"
import FeatureCard from "./common/FeatureCard"
import DataTable from "./common/DataTable"
import publicClient from "../api/publicClient"

function useFetchEvents(){
    const axios = publicClient
    return useQuery({
        queryKey: ['events'], 
        staleTime: 2*60*1000,
        refetchOnMount: true,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        
        queryFn: async () => {
                const response = await axios.get('/events') 
                return response.data;
        }
    })
}

function useFetchCameras(){
    const axios = publicClient
    return useQuery({
        queryKey: ['cameras'], 
        staleTime: 2*60*1000,
        refetchOnMount: true,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        
        queryFn: async () => {
                const response = await axios.get('/cameras') 
                return response.data;
        }
    })
}

const columns = [
  {
    key: "camera",
    header: "Camera",
    width: "120px",
    cell: (row) => row.id
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
  const { data: events = [], isLoading } = useFetchEvents()
  const { data: cameras = [] } = useFetchCameras()

  return (
    <FeatureCard
      title="Recent Events"
      showHeaderDivider
      className="mt-10"
    >
      <DataTable
        columns={columns}
        rows={events}
        getRowKey={(row) => row.id}
        emptyState={isLoading ? "Loading events..." : "No events detected."}
      />
    </FeatureCard>
  )
}