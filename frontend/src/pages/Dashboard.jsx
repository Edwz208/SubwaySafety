import CameraGrid from "../components/camera/CameraGrid";
import Button from "../components/common/Button";
import Modal from "../components/common/Modal";
import AddCameraForm from "../components/camera/AddCameraForm";
import EventTableCard from "../components/EventTable";

import { useState } from 'react'

const DashboardHome = () => {
    const [isAdd, setIsAdd] = useState(false)

    return (
        <div className="w-[90%] mx-auto">
            <div className="mt-5 flex items-center justify-between mb-10">
            <h1 className='text-3xl'>Welcome To Dashboard</h1>
            <Button onClick={()=>{setIsAdd(true)}}>+ Add Camera</Button>
            </div>
            <CameraGrid/>
            <Modal
                isOpen={isAdd}
                onClose={() => setIsAdd(false)}
                title="Add New Camera"
            >
                <AddCameraForm
                onSuccess={() => setIsAdd(false)}
                onCancel={() => setIsAdd(false)}
                />
            </Modal>
            <EventTableCard />
        </div>
    )
}

export default DashboardHome;