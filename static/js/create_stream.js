new Vue({
    el: '#app',
    data: {
        streamName: '',
        file: null,
        trainingStatus: "Start Training",
        customQuestion: '',
    },
    methods: {
        handleFileUpload(event) {
            this.file = event.target.files[0];
        },
        submitStream() {
            const formData = new FormData();
            formData.append('streamName', this.streamName);
            formData.append('file', this.file);
            formData.append('customQuestion', this.customQuestion);

            this.trainingStatus = "Started";

            axios.post('/beefystew/create_stream', formData)
                .then(response => {
                    this.trainingStatus = "Finished";
                    console.log(response.data);
                    if (response.data.error) {
                        this.trainingStatus = "Failed";
                        console.error(response.data.error);
                    } else {
                        window.location.href = `/beefystew/stream/${response.data.stream_id}`;
                    }
                })
                .catch(error => {
                    console.error(error);
                });
        }
    }
});
