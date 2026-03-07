import useAlertWS from '../hooks/useAlertWS'
import { useState } from 'react'

function DisplayAlert(){
    const [display, setDisplay] = useState({})
    const { isOpen } = useAlertWS({ onMessage: (data) => {

    }});

    if (!isOpen){
        return <div>Connecting to server...</div>
    }
    return (
        <div className=''>yes</div>
    )
}

export default DisplayAlert;