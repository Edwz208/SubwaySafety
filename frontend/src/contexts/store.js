import { create } from 'zustand';

const useStore = create((set)=>{
    return{
        accessToken: null,
        setAccessToken: (value)=> (set({accessToken: value})),
        isLogged: false,
        setLogged: (bool) =>{ 
            set({isLogged: bool})
        
        },
        clearData: ()=>{set({accessToken: null, isLogged: false})}
    }
})

export default useStore;