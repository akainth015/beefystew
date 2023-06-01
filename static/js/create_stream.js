new Vue({
  el: '#app',
  data: {
    streamName: '',
    file: null
  },
  methods: {
    handleFileUpload(event) {
      this.file = event.target.files[0];
    },
    submitStream() {
      const formData = new FormData();
      formData.append('streamName', this.streamName);
      formData.append('file', this.file);

      axios.post('/beefystew/create_stream', formData)
        .then(response => {
          console.log(response.data);
          if (response.data.error) {
              console.error(response.data.error);
          } else {
              window.location.href = '/beefystew/index';
          }
        })
        .catch(error => {
          console.error(error);
        });
    }
  }
});