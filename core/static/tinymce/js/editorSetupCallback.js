function editorSubmitHandler(event) {
    event.preventDefault()  // prevent default behavior to avoid saving images as base64

    tinymce.activeEditor.uploadImages()
        .then(
            (result) => {
                const hasNotUploadedImages = result.some((el) => !el.status)

                // submit form only if all images were uploaded
                if (!hasNotUploadedImages) {
                    event.target.submit()
                }
            }
        )
}


function editorSetupCallback(editor) {
    editor.on('submit', editorSubmitHandler)
}