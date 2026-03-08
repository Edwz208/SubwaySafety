import FeatureCard from "../common/FeatureCard";
import { useQuery } from "@tanstack/react-query";
import publicClient from '../../api/publicClient'
import useAlertWS from "../../hooks/useAlertWS";

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

function CameraGrid({ onSelectCamera }) {
    const { isOpen } = useAlertWS({ onMessage: (data) => {
    }});
    const  {data, isLoading, isError, error} = useFetchCameras()
    const errorMessage = error?.response ? (error.response.data?.detail ||error.response.status) : error?.request ? "Server unreachable. Check your connection." : (error?.message || "Unexpected error");
    if (isError) {
        const status = error?.response?.status
        if (status === 401){
            return <div>Unauthorized</div>
        }
        return <p>Error: {errorMessage}</p>}
    if (isLoading) return <div>Loading cameras...</div>
    const cameras = data || []
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {cameras.map((camera) => (
        <FeatureCard
          key={camera.id}
          title={camera.name}
          bg="background"
          onClick={() => {
            if (typeof onSelectCamera === 'function') {
              onSelectCamera(camera.id);
            }
          }}
        >
          <div className="flex flex-col gap-2">
            <video
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-full object-cover rounded-xl"
                >
            <source src="https://www.w3schools.com/html/mov_bbb.mp4" type="video/mp4" />
            </video>
            <p className="text-sm text-muted">
              {camera.location}
            </p>

            <p className="text-sm">
              Status: {camera.is_detected ? "⚠️ Detection" : "✅ Clear"}
            </p>

            <p className="text-sm">
              Connection: "🟢 Online"
            </p>

          </div>
        </FeatureCard>
      ))}
    </div>
  );
}

export default CameraGrid;