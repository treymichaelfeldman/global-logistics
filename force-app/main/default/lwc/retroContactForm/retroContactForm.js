import { LightningElement } from 'lwc';

export default class RetroContactForm extends LightningElement {
    handleSubmit(event) {
        event.preventDefault();
        alert('Error: Mail server offline. Please call 1-800-GLOBAL-99 instead!');
    }
}