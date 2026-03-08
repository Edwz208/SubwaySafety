import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "../common/Button";
import publicClient from "../../api/publicClient";

function AddCameraForm({ onSuccess, onCancel }) {
  const axios = publicClient
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    name: "",
    location: "",
    url: "",
  });

  const [formError, setFormError] = useState("");

  const createCameraMutation = useMutation({
    mutationFn: async (payload) => {
      const response = await axios.post("/cameras", payload);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
      if (typeof onSuccess === "function") {
        onSuccess();
      }
    },
    onError: (error) => {
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        "Failed to create camera.";
      setFormError(message);
    },
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setFormError("");
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  function handleSubmit(e) {
    e.preventDefault();

    const trimmed = {
      name: formData.name.trim(),
      location: formData.location.trim(),
      url: formData.url.trim(),
    };

    if (!trimmed.name || !trimmed.location || !trimmed.url) {
      setFormError("All fields are required.");
      return;
    }

    createCameraMutation.mutate(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label htmlFor="name" className="text-sm font-medium">
          Camera Name
        </label>
        <input
          id="name"
          name="name"
          type="text"
          value={formData.name}
          onChange={handleChange}
          placeholder="Enter camera name"
          className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="location" className="text-sm font-medium">
          Location
        </label>
        <input
          id="location"
          name="location"
          type="text"
          value={formData.location}
          onChange={handleChange}
          placeholder="Enter location"
          className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="url" className="text-sm font-medium">
           URL
        </label>
        <input
          id="url"
          name="url"
          type="text"
          value={formData.url}
          onChange={handleChange}
          placeholder="://..."
          className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
        />
      </div>

      {formError ? (
        <p className="text-sm text-red-500">{formError}</p>
      ) : null}

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" onClick={onCancel}>
          Cancel
        </Button>

        <Button type="submit" disabled={createCameraMutation.isPending}>
          {createCameraMutation.isPending ? "Creating..." : "Create Camera"}
        </Button>
      </div>
    </form>
  );
}

export default AddCameraForm;