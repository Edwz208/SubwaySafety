// import { useMutation, useQueryClient } from '@tanstack/react-query'
// import privateClient from '../api/privateClient'

// export function useCreateUser(onSuccessCallback, onErrorCallback){
//   const queryClient = useQueryClient()
//   return useMutation({
//       mutationFn: async (formData) => {
//           const response = await privateClient.post('/create-user', formData)
//           return response?.data;
//       },
//     onSuccess: (data)=>{  
//       queryClient.setQueryData(['user'], data?.user)
//       if (onSuccessCallback && typeof onSuccessCallback === 'function') onSuccessCallback()
//     },
//     onError: (error)=>{
//       if (onErrorCallback && typeof onErrorCallback === 'function') onErrorCallback(error)
//     }
//   })

// }